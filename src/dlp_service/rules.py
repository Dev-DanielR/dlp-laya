"""Rule-based candidate span finder (Laya Experts demo shape + PE lab patterns)."""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass

# Keep label vocabulary aligned with goku-san/laya-experts pii flavour.
LABEL_MAP: dict[str, str] = {
    "GIVENNAME": "given name",
    "SURNAME": "surname",
    "TITLE": "title",
    "GENDER": "gender",
    "SEX": "sex",
    "AGE": "age",
    "DATE": "date",
    "EMAIL": "email address",
    "TELEPHONENUM": "phone number",
    "SOCIALNUM": "social security number",
    "TAXNUM": "tax number",
    "IDCARDNUM": "id card number",
    "PASSPORTNUM": "passport number",
    "DRIVERLICENSENUM": "driver licence number",
    "CREDITCARDNUMBER": "credit card number",
    "STREET": "street",
    "BUILDINGNUM": "building number",
    "CITY": "city",
    "ZIPCODE": "postal code",
    "TIME": "time",
    "URL": "web address",
}
NOT_PII = "not pii"
LABELS = list(LABEL_MAP.values()) + [NOT_PII]

INSTRUCTIONS = (
    "A candidate span of text was pulled out of a document, and is shown with the text either "
    "side of it. Which kind of personal data is the span itself, or is it not personal data at "
    "all? Judge the span, not the surrounding text."
)

CONTEXT_CHARS = 400

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    "|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
)

FAMILIES: dict[str, str] = {
    "EMAIL": r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    "DATE_ISO": r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?",
    "DATE_NUMERIC": r"\b\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}\b",
    "DATE_WORDY": rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?(?:{MONTHS})\.?(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?(?:,?\s*\d{{4}})?\b",
    "CARD": r"\b(?:\d{4}[ \-]?){3}\d{1,4}\b",
    "PHONE": r"(?:\+\d{1,3}[ .\-]?)?(?:\(\d{1,4}\)[ .\-]?)?\d{2,5}(?:[ .\-]\d{2,6}){1,4}",
    "PHONE_RUN": r"\+?\d[\d ().\-]{7,}\d",
    # Peru lab surfaces
    "PE_DNI": r"\b[1-7]\d{7}\b",
    "PE_RUC": r"\b20\d{9}\b",
    "PE_CCI": r"\b\d{3}-\d{1}-\d{12}\b",
    "PE_PHONE": r"\+51\s*9\d{2}\s*\d{3}\s*\d{3}",
    "ALNUM_ID": r"\b(?=[A-Za-z0-9\-]*\d)(?=[A-Za-z0-9\-]*[A-Za-z])[A-Za-z0-9][A-Za-z0-9\-]{4,}\b",
    "POSTCODE_NUM": r"\b\d{4,6}(?:-\d{4})?\b",
    "BARE_INT": r"\b\d{1,15}\b",
    "URLISH": r"\b(?:https?://|www\.)[^\s,;]+",
    "SSN_DASH": r"\b\d{3}-\d{2}-\d{4}\b",
}

_CASE_INSENSITIVE = ("URLISH",)
COMPILED = {
    k: re.compile(v, re.IGNORECASE if k in _CASE_INSENSITIVE else 0)
    for k, v in FAMILIES.items()
}

WORD_TOKEN = re.compile(r"\w[\w'’.\-]*", re.UNICODE)
CAPS_MAX_RUN = 5
PARTICLES = {
    "van",
    "von",
    "de",
    "del",
    "della",
    "der",
    "den",
    "da",
    "di",
    "du",
    "la",
    "le",
    "y",
    "e",
    "de",
}


@dataclass(frozen=True)
class Candidate:
    start: int
    end: int
    text: str
    families: tuple[str, ...]


def propose_spans(text: str, max_run: int = CAPS_MAX_RUN) -> dict[tuple[int, int], list[str]]:
    out: dict[tuple[int, int], list[str]] = collections.defaultdict(list)
    for name, rx in COMPILED.items():
        for m in rx.finditer(text):
            s, e = m.span()
            while e > s and text[e - 1] in " .,;:-":
                e -= 1
            if e > s:
                out[(s, e)].append(name)

    toks: list[tuple[int, int, str]] = []
    for m in WORD_TOKEN.finditer(text):
        w = m.group(0)
        kind = (
            "cap"
            if w[:1].isupper()
            else ("particle" if w.lower().strip(".") in PARTICLES else None)
        )
        if kind:
            toks.append((m.start(), m.end(), kind))
    runs: list[list[tuple[int, int, str]]] = []
    for tk in toks:
        if runs and text[runs[-1][-1][1] : tk[0]].strip() in ("", "-"):
            runs[-1].append(tk)
        else:
            runs.append([tk])
    for run in runs:
        if not any(t[2] == "cap" for t in run):
            continue
        for i in range(len(run)):
            if run[i][2] == "particle":
                continue
            for j in range(i, min(i + max_run, len(run))):
                if run[j][2] == "particle":
                    continue
                s, e = run[i][0], run[j][1]
                while e > s and text[e - 1] in ".,;:-":
                    e -= 1
                if e > s:
                    out[(s, e)].append("CAPS_RUN" if j > i else "CAPS_SINGLE")
    return dict(out)


def candidates(text: str) -> list[Candidate]:
    rows: list[Candidate] = []
    for (s, e), fams in sorted(propose_spans(text).items()):
        rows.append(Candidate(start=s, end=e, text=text[s:e], families=tuple(fams)))
    return rows


def build_states(text: str, region: str = "US") -> list[tuple[Candidate, dict]]:
    """One model input per candidate, key order matching Laya Experts training."""
    rows: list[tuple[Candidate, dict]] = []
    for cand in candidates(text):
        s, e = cand.start, cand.end
        rows.append(
            (
                cand,
                {
                    "document_type": "unknown",
                    "language": "English",
                    "region": region,
                    "left": text[max(0, s - CONTEXT_CHARS) : s],
                    "span": text[s:e],
                    "right": text[e : e + CONTEXT_CHARS],
                },
            )
        )
    return rows
