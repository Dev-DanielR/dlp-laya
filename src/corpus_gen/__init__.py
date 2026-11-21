"""Andes Advisory synthetic corpus generator for DAP Laya."""

from .generate import generate_corpus, load_manifest, summarize, validate_manifest

__all__ = [
    "generate_corpus",
    "load_manifest",
    "summarize",
    "validate_manifest",
]

__version__ = "1.0.0"
