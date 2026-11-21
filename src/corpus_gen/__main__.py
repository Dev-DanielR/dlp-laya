"""python -m corpus_gen — CLI entry (requires src on PYTHONPATH)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .generate import (
    DEFAULT_MANIFEST,
    DEFAULT_OUT,
    DEFAULT_SEED,
    generate_corpus,
)
from .llm import DEFAULT_CACHE_ROOT, DEFAULT_HOST, DEFAULT_MODEL
from .templates import TEMPLATES


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Generate the Andes Advisory synthetic corpus under data/files/. "
            "Reads data/manifest.json and materializes each record with a deterministic seed."
        )
    )
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--dry-run", action="store_true", help="Validate and summarize only")
    p.add_argument(
        "--no-update-manifest",
        action="store_true",
        help="Do not rewrite manifest.json with concrete spans/offsets",
    )
    p.add_argument("--list-templates", action="store_true")
    p.add_argument(
        "--llm",
        action="store_true",
        help="Use Ollama for body paragraphs (cached under data/corpus_bodies/)",
    )
    p.add_argument(
        "--refresh-llm",
        action="store_true",
        help="Ignore LLM cache and regenerate bodies",
    )
    p.add_argument(
        "--llm-required",
        action="store_true",
        help="Fail if any Ollama call fails (default: soft-fallback)",
    )
    p.add_argument(
        "--ollama-model",
        default=os.environ.get("CORPUS_OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Ollama model tag (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--ollama-host",
        default=os.environ.get("CORPUS_OLLAMA_HOST", DEFAULT_HOST),
        help=f"Ollama base URL (default: {DEFAULT_HOST})",
    )
    p.add_argument(
        "--llm-cache",
        type=Path,
        default=DEFAULT_CACHE_ROOT,
        help="Directory for cached LLM body JSON",
    )
    args = p.parse_args(argv)

    if args.list_templates:
        for tid, desc in TEMPLATES.items():
            print(f"{tid}: {desc}")
        return 0

    return generate_corpus(
        manifest_path=args.manifest,
        out_root=args.out,
        seed=args.seed,
        dry_run=args.dry_run,
        update_manifest=not args.no_update_manifest,
        use_llm=args.llm,
        refresh_llm=args.refresh_llm,
        llm_required=args.llm_required,
        ollama_model=args.ollama_model,
        ollama_host=args.ollama_host,
        llm_cache_root=args.llm_cache,
    )


if __name__ == "__main__":
    raise SystemExit(main())
