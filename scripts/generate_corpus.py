#!/usr/bin/env python3
"""CLI shim: adds src/ to sys.path and runs corpus_gen."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from corpus_gen.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
