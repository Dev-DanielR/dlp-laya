"""Orchestrate corpus generation from manifest.json."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .content_packs import content_pack_for
from .llm import DEFAULT_CACHE_ROOT, DEFAULT_HOST, DEFAULT_MODEL, LlmStats, fetch_body_sections
from .pools import file_rng
from .spans import fill_span_values, person_for_record
from .templates import TEMPLATES, build_document, choose_variant
from .writers import write_file

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "manifest.json"
DEFAULT_OUT = ROOT / "data" / "files"
DEFAULT_SEED = 20261114


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "files" not in data:
        raise SystemExit(f"manifest missing 'files': {path}")
    return data


def summarize(files: list[dict[str, Any]]) -> None:
    labels = Counter(f["label"] for f in files)
    formats = Counter(f["format"] for f in files)
    templates = Counter(f["template"] for f in files)
    tags = Counter(tag for f in files for tag in f.get("case_tags", []))
    print(f"files: {len(files)}")
    print(f"labels: {dict(labels)}")
    print(f"formats: {dict(formats)}")
    print(f"templates: {dict(templates)}")
    print(f"case_tags: {dict(tags)}")


def validate_manifest(files: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for f in files:
        if f["id"] in ids:
            errors.append(f"duplicate id {f['id']}")
        ids.add(f["id"])
        if f["path"] in paths:
            errors.append(f"duplicate path {f['path']}")
        paths.add(f["path"])
        if f["template"] not in TEMPLATES:
            errors.append(f"{f['id']}: unknown template {f['template']}")
        if f["label"] not in ("limpio", "con_pii"):
            errors.append(f"{f['id']}: bad label {f['label']}")
        if f["format"] not in ("txt", "csv", "pdf", "docx", "bin"):
            errors.append(f"{f['id']}: bad format {f['format']}")
        spans = f.get("expected_spans") or []
        if f["label"] == "limpio" and spans and f["template"] != "corrupt_seed":
            errors.append(f"{f['id']}: limpio with spans")
        if f["label"] == "con_pii" and not spans:
            errors.append(f"{f['id']}: con_pii without spans")
        if f.get("fp_traps") and f["label"] != "limpio":
            errors.append(
                f"{f['id']}: fp_traps on non-limpio (policy: traps are clean distractors)"
            )
    return errors


def _post_validate_files(
    files: list[dict[str, Any]], out_root: Path
) -> list[str]:
    errors: list[str] = []
    for f in files:
        dest = out_root / f["path"]
        if not dest.is_file():
            errors.append(f"missing output: {dest}")
            continue
        if f["format"] in ("txt", "csv"):
            text = dest.read_text(encoding="utf-8")
            for span in f.get("expected_spans") or []:
                if span["text"] not in text:
                    errors.append(f"{f['id']}: span text missing in file: {span['type']}")
                if "start" in span and "end" in span:
                    slice_ = text[span["start"] : span["end"]]
                    if slice_ != span["text"]:
                        errors.append(
                            f"{f['id']}: bad offsets for {span['type']}: "
                            f"{slice_!r} != {span['text']!r}"
                        )
            for trap in f.get("fp_traps") or []:
                if trap == "sku_8dig":
                    # At least one 8-digit token should appear
                    import re

                    if not re.search(r"\b\d{8}\b", text):
                        errors.append(f"{f['id']}: sku_8dig trap not found")
                elif trap == "hotline" and "01-615-8000" not in text:
                    errors.append(f"{f['id']}: hotline trap not found")
                elif trap == "proyeccion" and "proyección" not in text.lower() and "proyeccion" not in text.lower():
                    errors.append(f"{f['id']}: proyeccion trap not found")
                elif trap == "confidencialidad" and "confidencialidad" not in text.lower():
                    errors.append(f"{f['id']}: confidencialidad trap not found")
                elif trap == "dni_mention":
                    if "DNI" not in text:
                        errors.append(f"{f['id']}: dni_mention trap not found")
        if f["template"] == "corrupt_seed" and dest.stat().st_size < 16:
            errors.append(f"{f['id']}: corrupt seed too small")
    return errors


def generate_corpus(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    out_root: Path = DEFAULT_OUT,
    seed: int = DEFAULT_SEED,
    dry_run: bool = False,
    update_manifest: bool = True,
    use_llm: bool = False,
    refresh_llm: bool = False,
    llm_required: bool = False,
    ollama_model: str = DEFAULT_MODEL,
    ollama_host: str = DEFAULT_HOST,
    llm_cache_root: Path = DEFAULT_CACHE_ROOT,
) -> int:
    data = load_manifest(manifest_path)
    files = data["files"]
    errors = validate_manifest(files)
    if errors:
        print("manifest validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"manifest: {manifest_path}")
    print(f"seed: {seed}")
    print(f"out: {out_root}")
    if use_llm:
        print(f"llm: on model={ollama_model} host={ollama_host} refresh={refresh_llm}")
    else:
        print("llm: off (deterministic fillers)")
    summarize(files)

    if dry_run:
        print("dry-run OK (no files written)")
        return 0

    out_root.mkdir(parents=True, exist_ok=True)
    updated: list[dict[str, Any]] = []
    stats = LlmStats()
    for record in files:
        # Mirror build_document rng consumption to learn variant for LLM prompt.
        rng_peek = file_rng(seed, record["id"])
        person = person_for_record(rng_peek, record["path"])
        expected = list(record.get("expected_spans") or [])
        if expected:
            fill_span_values(expected, person, rng_peek)
        variant = choose_variant(record["template"], rng_peek)

        body_sections: list[str] | None = None
        # CSV/bin layouts are structural; skip Ollama (saves time, cache stays useful for prose).
        if (
            use_llm
            and record["template"] != "corrupt_seed"
            and record["format"] not in ("csv", "bin")
        ):
            pack = content_pack_for(record["path"])
            body_sections = fetch_body_sections(
                file_id=record["id"],
                path=record["path"],
                template=record["template"],
                variant=variant,
                pack=pack,
                seed=seed,
                model=ollama_model,
                host=ollama_host,
                cache_root=llm_cache_root,
                refresh=refresh_llm,
                required=llm_required,
                stats=stats,
            ) or None

        rng = file_rng(seed, record["id"])
        canonical, spans, raw, _variant = build_document(
            record, rng, body_sections=body_sections, variant=variant
        )
        dest = out_root / record["path"]
        write_file(dest, record["format"], canonical, raw)

        new_rec = dict(record)
        new_rec["expected_spans"] = spans
        if record["format"] in ("pdf", "docx") and spans:
            new_rec["canonical_note"] = (
                "start/end refer to generator canonical text (pre PDF/DOCX layout)"
            )
        updated.append(new_rec)

    data["files"] = updated
    data["counts"] = {
        "total": len(updated),
        "con_pii": sum(1 for f in updated if f["label"] == "con_pii"),
        "limpio": sum(1 for f in updated if f["label"] == "limpio"),
    }
    data["seed_used"] = seed
    if use_llm:
        data["llm"] = {
            "model": ollama_model,
            "cache_hits": stats.hits,
            "cache_misses": stats.misses,
            "failures": stats.failures,
            "writes": stats.writes,
        }

    post = _post_validate_files(updated, out_root)
    if post:
        print("post-write validation failed:", file=sys.stderr)
        for e in post:
            print(f"  - {e}", file=sys.stderr)
        return 3

    if update_manifest:
        manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"updated manifest spans: {manifest_path}")

    if use_llm:
        print(
            f"llm stats: hits={stats.hits} misses={stats.misses} "
            f"writes={stats.writes} failures={stats.failures}"
        )
    print(f"wrote {len(updated)} files under {out_root}")
    return 0
