"""Decision matrix: f(sensibilidad, label) → completo | sanitizado | denegado."""

from __future__ import annotations

from typing import Literal

Sensitivity = Literal["alta", "media", "baja"]
Label = Literal["limpio", "con_pii"]
Decision = Literal["completo", "sanitizado", "denegado"]

_VALID_SENS = frozenset({"alta", "media", "baja"})
_VALID_LABELS = frozenset({"limpio", "con_pii"})


def decide(sensitivity: str, label: str) -> Decision:
    """Apply the README §6.1 matrix.

    limpio → completo for any sensitivity.
    con_pii → completo (alta) | sanitizado (media) | denegado (baja).
    """
    if sensitivity not in _VALID_SENS:
        raise ValueError(f"invalid sensitivity: {sensitivity!r}")
    # Normalize common variants from DLP
    norm_label = label.strip().lower().replace(" ", "_")
    if norm_label in {"con_pii", "con-pii", "pii"}:
        norm_label = "con_pii"
    elif norm_label in {"limpio", "clean"}:
        norm_label = "limpio"
    if norm_label not in _VALID_LABELS:
        raise ValueError(f"invalid label: {label!r}")

    if norm_label == "limpio":
        return "completo"
    if sensitivity == "alta":
        return "completo"
    if sensitivity == "media":
        return "sanitizado"
    return "denegado"
