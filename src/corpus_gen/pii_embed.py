"""Natural embedding styles for filled PII spans."""

from __future__ import annotations

import random
from typing import Any

from .pools import Person


def by_type(filled: list[dict[str, str]]) -> dict[str, str]:
    return {s["type"]: s["text"] for s in filled}


def embed_pii_block(
    filled: list[dict[str, str]],
    person: Person,
    rng: random.Random,
    *,
    styles: list[str] | None = None,
) -> list[str]:
    """Return lines that contain every filled span text exactly once per type."""
    if not filled:
        return []
    vals = by_type(filled)
    choices = styles or ["ficha", "signature", "email_header", "inline"]
    style = rng.choice(choices)
    if style == "signature":
        return _signature(vals, person)
    if style == "email_header":
        return _email_header(vals, person)
    if style == "inline":
        return _inline(vals, person)
    return _ficha(vals, person)


def ensure_all_span_texts(
    lines: list[str],
    filled: list[dict[str, str]],
) -> list[str]:
    """Append any missing span texts so locate_offsets can succeed."""
    body = "\n".join(lines)
    missing = [s for s in filled if s["text"] not in body]
    if not missing:
        return lines
    extra = ["", "--- Datos de referencia ---"]
    for s in missing:
        extra.append(f"{s['type']}: {s['text']}")
    return lines + extra


def _ficha(vals: dict[str, str], person: Person) -> list[str]:
    lines = [
        "Datos de contacto / identificación",
        f"Nombres: {vals.get('given_name', person.given_name)}",
        f"Apellidos: {vals.get('surname', person.surname)}",
    ]
    _append_common(lines, vals, labeled=True)
    return lines


def _signature(vals: dict[str, str], person: Person) -> list[str]:
    name = (
        f"{vals.get('given_name', person.given_name)} "
        f"{vals.get('surname', person.surname)}"
    )
    lines = [
        "Atentamente,",
        name,
    ]
    if "email_address" in vals:
        lines.append(vals["email_address"])
    if "phone_number" in vals:
        lines.append(f"Cel. {vals['phone_number']}")
    if "id_card_number" in vals:
        lines.append(f"DNI {vals['id_card_number']}")
    if "organization_tax_id" in vals:
        lines.append(f"RUC {vals['organization_tax_id']}")
    if "bank_account" in vals:
        lines.append(f"CCI {vals['bank_account']}")
    if "credit_card_number" in vals:
        lines.append(f"Tarjeta de referencia (lab): {vals['credit_card_number']}")
    if "street" in vals or "city" in vals:
        street = vals.get("street", person.street)
        city = vals.get("city", person.city)
        lines.append(f"{street}, {city}")
    if "postal_code" in vals:
        lines.append(f"CP {vals['postal_code']}")
    # Ensure given/surname appear as substrings even if only other types listed
    if "given_name" in vals and vals["given_name"] not in "\n".join(lines):
        lines.insert(1, vals["given_name"])
    if "surname" in vals and vals["surname"] not in "\n".join(lines):
        lines.insert(2, vals["surname"])
    return lines


def _email_header(vals: dict[str, str], person: Person) -> list[str]:
    name = (
        f"{vals.get('given_name', person.given_name)} "
        f"{vals.get('surname', person.surname)}"
    )
    lines = [
        f"De: {name}"
        + (f" <{vals['email_address']}>" if "email_address" in vals else ""),
        "Para: equipo.proyecto@andesadvisory.pe",
        "Asunto: Seguimiento de entregables",
    ]
    if "phone_number" in vals:
        lines.append(f"Tel: {vals['phone_number']}")
    _append_common(lines, vals, labeled=True, skip={"email_address", "phone_number"})
    # given/surname already in De: line when both present
    return lines


def _inline(vals: dict[str, str], person: Person) -> list[str]:
    gn = vals.get("given_name", person.given_name)
    sn = vals.get("surname", person.surname)
    parts = [f"Queda como punto de contacto {gn} {sn}"]
    if "id_card_number" in vals:
        parts.append(f"identificado/a con DNI {vals['id_card_number']}")
    if "email_address" in vals:
        parts.append(f"correo {vals['email_address']}")
    if "phone_number" in vals:
        parts.append(f"teléfono {vals['phone_number']}")
    if "organization_tax_id" in vals:
        parts.append(f"RUC {vals['organization_tax_id']}")
    if "bank_account" in vals:
        parts.append(f"CCI {vals['bank_account']}")
    if "credit_card_number" in vals:
        parts.append(f"tarjeta de referencia {vals['credit_card_number']}")
    if "street" in vals or "city" in vals:
        parts.append(
            f"domicilio en {vals.get('street', person.street)}, "
            f"{vals.get('city', person.city)}"
        )
    if "postal_code" in vals:
        parts.append(f"código postal {vals['postal_code']}")
    sentence = ", ".join(parts) + "."
    return [sentence]


def _append_common(
    lines: list[str],
    vals: dict[str, str],
    *,
    labeled: bool,
    skip: set[str] | None = None,
) -> None:
    skip = skip or set()
    mapping = [
        ("id_card_number", "DNI"),
        ("email_address", "Correo"),
        ("phone_number", "Teléfono"),
        ("organization_tax_id", "RUC"),
        ("bank_account", "CCI"),
        ("credit_card_number", "Tarjeta (lab)"),
        ("street", "Dirección"),
        ("city", "Ciudad"),
        ("postal_code", "Código postal"),
    ]
    for key, label in mapping:
        if key in skip or key not in vals:
            continue
        if labeled:
            lines.append(f"{label}: {vals[key]}")
        else:
            lines.append(vals[key])
