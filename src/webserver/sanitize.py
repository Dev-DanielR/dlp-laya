"""Apply PII spans to file bytes without mutating the original on disk."""

from __future__ import annotations

from typing import Any


def redact_token(span_type: str | None) -> str:
    kind = (span_type or "pii").strip() or "pii"
    return f"[REDACTED:{kind}]"


def apply_spans(data: bytes, spans: list[dict[str, Any]]) -> bytes:
    """Return a redacted copy of ``data``.

    Prefer start/end offsets when the slice matches ``text``.
    Otherwise replace exact UTF-8 occurrences of ``text``.
    Longer texts are applied first; ranges do not overlap.
    """
    if not spans:
        return data

    prepared: list[tuple[int, int, str, str]] = []
    # (start, end, text, type) for offset-based; start=-1 for text-only
    for span in spans:
        text = span.get("text")
        if not text:
            continue
        stype = span.get("type")
        start = span.get("start")
        end = span.get("end")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end:
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                decoded = None
            if decoded is not None and end <= len(decoded) and decoded[start:end] == text:
                prepared.append((start, end, text, stype or "pii"))
                continue
        prepared.append((-1, -1, text, stype or "pii"))

    # Offset-based: apply from the end so indices stay valid
    offset_spans = sorted(
        [p for p in prepared if p[0] >= 0],
        key=lambda x: x[0],
        reverse=True,
    )
    text_only = [p for p in prepared if p[0] < 0]
    text_only.sort(key=lambda x: len(x[2]), reverse=True)

    try:
        text = data.decode("utf-8")
        used_text = True
    except UnicodeDecodeError:
        return _apply_bytes(data, prepared)

    # Mark covered ranges for offset replacements
    covered: list[tuple[int, int]] = []
    chars = list(text)

    def overlaps(a: int, b: int) -> bool:
        for c0, c1 in covered:
            if a < c1 and b > c0:
                return True
        return False

    for start, end, _txt, stype in offset_spans:
        if overlaps(start, end):
            continue
        token = redact_token(stype)
        chars[start:end] = list(token)
        # After list splice, covered indices in original space still OK for later
        # higher starts only (we go descending).
        covered.append((start, end))

    result = "".join(chars)

    # Text-only replacements on the current string (skip if already redacted away)
    for _s, _e, needle, stype in text_only:
        token = redact_token(stype)
        if needle in result:
            result = result.replace(needle, token)

    return result.encode("utf-8")


def _apply_bytes(data: bytes, prepared: list[tuple[int, int, str, str]]) -> bytes:
    """Best-effort replacement on raw bytes via UTF-8 encodings of span text."""
    out = data
    items = sorted(prepared, key=lambda x: len(x[2]), reverse=True)
    for _s, _e, needle, stype in items:
        nb = needle.encode("utf-8")
        token = redact_token(stype).encode("utf-8")
        if nb in out:
            out = out.replace(nb, token)
    return out
