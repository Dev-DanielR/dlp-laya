from pathlib import Path

from webserver.sanitize import apply_spans


def test_offset_replace():
    text = "hola 12345678 mundo"
    data = text.encode("utf-8")
    out = apply_spans(
        data,
        [{"type": "dni", "text": "12345678", "start": 5, "end": 13}],
    )
    assert out.decode("utf-8") == "hola [REDACTED:dni] mundo"


def test_text_replace_and_disk_untouched(tmp_path):
    path = tmp_path / "doc.txt"
    original = "contacto: ana@example.com fin"
    path.write_text(original, encoding="utf-8")
    raw = path.read_bytes()
    out = apply_spans(raw, [{"type": "email", "text": "ana@example.com"}])
    assert b"[REDACTED:email]" in out
    assert path.read_text(encoding="utf-8") == original


def test_longest_first():
    data = b"abcd"
    out = apply_spans(
        data,
        [
            {"type": "a", "text": "bc"},
            {"type": "b", "text": "abcd"},
        ],
    )
    assert out == b"[REDACTED:b]"
