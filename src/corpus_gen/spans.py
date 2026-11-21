"""Fill expected_spans placeholders and locate character offsets."""

from __future__ import annotations

import random
from typing import Any

from .pools import Person, make_person, value_for_type


def fill_span_values(
    expected_spans: list[dict[str, Any]],
    person: Person,
    rng: random.Random,
) -> list[dict[str, str]]:
    """Return [{type, text}, ...] derived from person (seed-deterministic).

    Prior concrete texts in the manifest are ignored so regeneration with the
    same seed stays reproducible after pool fixes.
    """
    filled: list[dict[str, str]] = []
    for span in expected_spans:
        stype = span["type"]
        filled.append({"type": stype, "text": value_for_type(person, stype, rng)})
    return filled


def locate_offsets(canonical: str, spans: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Attach start/end for each span by sequential search in canonical text."""
    cursor = 0
    out: list[dict[str, Any]] = []
    for span in spans:
        text = span["text"]
        idx = canonical.find(text, cursor)
        if idx < 0:
            idx = canonical.find(text)
        if idx < 0:
            raise ValueError(
                f"span text not found in canonical body: type={span['type']!r} text={text!r}"
            )
        end = idx + len(text)
        out.append({"type": span["type"], "text": text, "start": idx, "end": end})
        cursor = end
    return out


def person_for_record(rng: random.Random, path: str) -> Person:
    """Pick email domain hint from path when possible."""
    domain = None
    lower = path.lower()
    if "banco_andino" in lower:
        domain = "bancoandino.pe"
    elif "retail_pacifico" in lower:
        domain = "retailpacifico.pe"
    elif "minera_sierra" in lower:
        domain = "minerasierra.pe"
    elif "clinica_salud" in lower:
        domain = "clinicasaludlima.pe"
    elif "agro_valle" in lower:
        domain = "agrovalle.pe"
    elif "interno" in lower or "rrhh" in lower:
        domain = "andesadvisory.pe"
    return make_person(rng, domain=domain)
