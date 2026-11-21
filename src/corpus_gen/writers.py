"""Write canonical text to txt / csv / pdf / docx / bin."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fpdf import FPDF

_LABEL_VALUE = re.compile(r"^([^:]{2,40}):\s+(.+)$")
_LIST_ITEM = re.compile(r"^(\- |\* |• |\d+\.\d*\s+|\d+\)\s+|\[\s?[xX ]?\])")


def write_file(path: Path, fmt: str, canonical: str, raw: bytes | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "bin":
        if raw is None:
            raise ValueError("bin format requires raw bytes")
        path.write_bytes(raw)
        return
    if fmt in ("txt", "csv"):
        path.write_text(canonical, encoding="utf-8", newline="\n")
        return
    if fmt == "pdf":
        _write_pdf(path, canonical)
        return
    if fmt == "docx":
        _write_docx(path, canonical)
        return
    raise ValueError(f"unsupported format: {fmt}")


def _system_font() -> Path | None:
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _fold_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _is_heading_candidate(line: str, index: int) -> bool:
    if index == 0:
        return True
    if line.isupper() and len(line) > 8:
        return True
    if line.startswith(("INFORME", "PROCEDIMIENTO", "RRHH", "COMPROBANTE", "EXTRACTO", "CHECKLIST", "RUNBOOK", "POLÍTICA", "Andes Advisory")):
        return True
    return False


def _flush_label_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    if len(rows) < 3:
        for label, value in rows:
            doc.add_paragraph(f"{label}: {value}")
        return
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(rows):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value


def _write_docx(path: Path, canonical: str) -> None:
    doc = Document()
    lines = canonical.splitlines()
    pending_table: list[tuple[str, str]] = []
    title_done = False

    def flush_table() -> None:
        nonlocal pending_table
        if pending_table:
            _flush_label_table(doc, pending_table)
            pending_table = []

    for i, line in enumerate(lines):
        if not line.strip():
            flush_table()
            continue
        m = _LABEL_VALUE.match(line)
        if m and not _LIST_ITEM.match(line):
            pending_table.append((m.group(1).strip(), m.group(2).strip()))
            continue
        flush_table()
        if not title_done and _is_heading_candidate(line, i):
            p = doc.add_heading(line, level=1)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            title_done = True
            continue
        if _LIST_ITEM.match(line):
            style = "List Number" if re.match(r"^\d+", line) else "List Bullet"
            # Strip common markers for cleaner list text
            text = re.sub(r"^(\- |\* |• |\d+\.\d*\s+|\d+\)\s+)", "", line)
            text = re.sub(r"^\[\s?[xX ]?\]\s*", "", text)
            try:
                doc.add_paragraph(text, style=style)
            except KeyError:
                doc.add_paragraph(line)
            continue
        if re.match(r"^\d+\.\s+\S", line) and len(line) < 80:
            doc.add_heading(line, level=2)
            continue
        doc.add_paragraph(line)

    flush_table()
    doc.save(str(path))


def _write_pdf(path: Path, canonical: str) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _system_font()
    if font is not None:
        pdf.add_font("CorpusSans", fname=str(font))
        pdf.add_font("CorpusSans", style="B", fname=str(font))
        body_font = "CorpusSans"
        body = canonical
    else:
        body_font = "Helvetica"
        body = _fold_ascii(canonical)

    lines = body.splitlines()
    for i, line in enumerate(lines):
        pdf.set_x(pdf.l_margin)
        if not line.strip():
            pdf.ln(4)
            continue
        if i == 0 or (line.isupper() and len(line) > 8):
            pdf.set_font(body_font, style="B" if body_font == "CorpusSans" else "", size=13)
            pdf.multi_cell(pdf.epw, 7, line)
            pdf.set_font(body_font, size=11)
            continue
        if re.match(r"^\d+\.\s+\S", line) and len(line) < 80:
            pdf.set_font(body_font, style="B" if body_font == "CorpusSans" else "", size=11)
            pdf.multi_cell(pdf.epw, 6, line)
            pdf.set_font(body_font, size=11)
            continue
        pdf.set_font(body_font, size=11)
        pdf.multi_cell(pdf.epw, 6, line if line else " ")
    pdf.output(str(path))
