"""Extract plain text from corpus file formats for classification."""

from __future__ import annotations

from pathlib import Path


def extract_text(path: Path) -> str:
    """Return Unicode text for PII scanning; empty if unreadable / binary."""
    suffix = path.suffix.lower()
    try:
        raw = path.read_bytes()
    except OSError:
        return ""

    if suffix in {".txt", ".csv", ".md", ".log", ".json", ".yaml", ".yml"}:
        return _decode(raw)

    if suffix == ".docx":
        return _docx_text(path)

    if suffix == ".pdf":
        return _pdf_text(path)

    # .bin and unknown: try UTF-8; empty on failure (corrupt seed stays limpio).
    return _decode(raw)


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def _docx_text(path: Path) -> str:
    try:
        from docx import Document
    except ImportError:
        return _decode(path.read_bytes())
    try:
        doc = Document(str(path))
    except Exception:  # noqa: BLE001
        return ""
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append("\t".join(cells))
    return "\n".join(parts)


def _pdf_text(path: Path) -> str:
    # Prefer pypdf if present; otherwise best-effort latin-1 from raw bytes.
    try:
        from pypdf import PdfReader
    except ImportError:
        return _decode(path.read_bytes())
    try:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t:
                chunks.append(t)
        return "\n".join(chunks)
    except Exception:  # noqa: BLE001
        return ""
