"""Optional Ollama-assisted body paragraphs with on-disk cache."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .content_packs import ContentPack

PROMPT_VERSION = 1
DEFAULT_MODEL = os.environ.get("CORPUS_OLLAMA_MODEL", "mistral-nemo:latest")
DEFAULT_HOST = os.environ.get("CORPUS_OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_CACHE_ROOT = Path(__file__).resolve().parents[2] / "data" / "corpus_bodies"

_PII_LINE = re.compile(
    r"("
    r"\b\d{8}\b|"  # DNI-like
    r"\b20\d{9}\b|"  # RUC-like
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|"
    r"\+51\s*\d|"
    r"\bCCI\b|"
    r"\b002-1-\d+"
    r")",
    re.IGNORECASE,
)


class LlmStats:
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.failures = 0
        self.writes = 0


def cache_path(cache_root: Path, seed: int, file_id: str, model: str) -> Path:
    safe_model = model.replace(":", "_").replace("/", "_")
    return cache_root / str(seed) / safe_model / f"v{PROMPT_VERSION}_{file_id}.json"


def fetch_body_sections(
    *,
    file_id: str,
    path: str,
    template: str,
    variant: str,
    pack: ContentPack,
    seed: int,
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    cache_root: Path = DEFAULT_CACHE_ROOT,
    refresh: bool = False,
    required: bool = False,
    stats: LlmStats | None = None,
) -> list[str]:
    """Return clean prose paragraphs; empty list on soft failure."""
    stats = stats or LlmStats()
    cpath = cache_path(cache_root, seed, file_id, model)
    if not refresh and cpath.is_file():
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
            sections = [s for s in data.get("sections", []) if isinstance(s, str)]
            if sections:
                stats.hits += 1
                return sections
        except (OSError, json.JSONDecodeError):
            pass

    stats.misses += 1
    prompt = _build_prompt(path=path, template=template, variant=variant, pack=pack)
    try:
        raw = _ollama_generate(host=host, model=model, prompt=prompt)
        sections = sanitize_sections(raw)
        if not sections:
            raise RuntimeError("empty LLM sections after sanitize")
        cpath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "file_id": file_id,
            "path": path,
            "variant": variant,
            "sections": sections,
        }
        cpath.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        stats.writes += 1
        return sections
    except Exception as exc:  # noqa: BLE001 — soft-fail unless required
        stats.failures += 1
        if required:
            raise RuntimeError(f"LLM required but failed for {file_id}: {exc}") from exc
        print(f"warn: LLM fallback for {file_id}: {exc}")
        return []


def sanitize_sections(raw: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw.strip()) if p.strip()]
    cleaned: list[str] = []
    for part in parts:
        lines = []
        for line in part.splitlines():
            if _PII_LINE.search(line):
                continue
            # Drop bullet markers that look like invented IDs
            lines.append(line.rstrip())
        text = "\n".join(lines).strip()
        if len(text) >= 40:
            cleaned.append(text)
    return cleaned[:6]


def _build_prompt(
    *,
    path: str,
    template: str,
    variant: str,
    pack: ContentPack,
) -> str:
    lexicon = ", ".join(pack.lexicon[:6])
    topics = ", ".join(pack.topics[:4])
    return (
        "Eres un redactor corporativo de Andes Advisory S.A.C. (consultora en Lima, Perú).\n"
        "Escribe SOLO en español peruano, tono profesional, sin markdown ni listas numeradas "
        "salvo que el párrafo lo pida de forma narrativa.\n"
        "PROHIBIDO inventar o mencionar: DNI, RUC, CCI, correos electrónicos, teléfonos, "
        "números de tarjeta, direcciones postales o nombres propios de personas.\n"
        "Devuelve entre 3 y 5 párrafos separados por una línea en blanco.\n"
        f"Cliente/contexto: {pack.display_name} ({pack.sector}).\n"
        f"Ruta del archivo: {path}\n"
        f"Plantilla: {template}; variante: {variant}.\n"
        f"Léxico sugerido: {lexicon}.\n"
        f"Temas sugeridos: {topics}.\n"
    )


def _ollama_generate(*, host: str, model: str, prompt: str, timeout: int = 120) -> str:
    url = host.rstrip("/") + "/api/generate"
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 500},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ollama unreachable at {host}: {exc}") from exc
    text = payload.get("response")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("ollama returned empty response")
    return text
