"""Canonical text builders per CORPUS.md template ID."""

from __future__ import annotations

import csv
import io
import random
from typing import Any

from .content_packs import ContentPack, content_pack_for
from .pii_embed import by_type, embed_pii_block, ensure_all_span_texts
from .pools import (
    AREAS,
    HOTLINE,
    INVOICE_CONCEPTS,
    JOB_TITLES,
    PROJECT_CODES,
    RISK_IDS,
    Person,
    make_person,
    make_sku,
)
from .spans import fill_span_values, locate_offsets, person_for_record

TEMPLATES: dict[str, str] = {
    "boletin_catalogo": "Public bulletin/catalog; optional FP traps (SKU, hotline, lexicon)",
    "client_contact_list": "CSV/table of client contacts (Informe CASO 02 columns)",
    "informe_proyecto": "Project narrative report; may embed contact PII",
    "contrato_extracto": "Contract/NDA extract with parties and domicile",
    "nota_rrhh": "HR note or roster row with collaborator PII",
    "factura_liquidacion": "Invoice/settlement with RUC, CCI, billing contact",
    "procedimiento_ops": "Internal procedure; clean; may mention confidencialidad",
    "corrupt_seed": "Unreadable bytes; classify as read-error, not PII",
}

_BOLETIN_VARIANTS = ("newsletter", "faq", "brochure", "press", "catalog")
_INFORME_VARIANTS = ("weekly", "kickoff", "riesgos", "acta")
_PROC_VARIANTS = ("sop", "checklist", "runbook", "politica")
_RRHH_VARIANTS = ("ficha", "memo", "politica")
_FACTURA_VARIANTS = ("factura", "liquidacion", "cci_notice")
_CONTRATO_VARIANTS = ("nda", "clausulas", "checklist_legal")


def _inject_fp_traps(lines: list[str], fp_traps: list[str], rng: random.Random) -> None:
    if "sku_8dig" in fp_traps:
        lines.append(f"Código de producto / SKU de referencia: {make_sku(rng)}")
    if "hotline" in fp_traps:
        lines.append(f"Mesa de ayuda corporativa: {HOTLINE}")
    if "proyeccion" in fp_traps:
        lines.append(
            "La proyección de demanda para el próximo trimestre se mantiene estable."
        )
    if "confidencialidad" in fp_traps:
        lines.append(
            "Este documento recuerda el compromiso de confidencialidad con clientes."
        )
    if "dni_mention" in fp_traps:
        lines.append(
            "Para validar identidad se podrá solicitar el DNI del titular sin consignar "
            "el número en este material."
        )


def _title_from_path(path: str) -> str:
    stem = path.rsplit("/", 1)[-1]
    for ext in (".txt", ".csv", ".pdf", ".docx", ".bin"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return stem.replace("_", " ").replace("-", " ").title()


def _pick(rng: random.Random, items: tuple[str, ...] | list[str], n: int = 1) -> list[str]:
    pool = list(items)
    rng.shuffle(pool)
    return pool[:n]


def _merge_body(lines: list[str], body_sections: list[str] | None, pack: ContentPack, rng: random.Random) -> None:
    sections = list(body_sections or [])
    if not sections:
        sections = list(_pick(rng, list(pack.filler_paragraphs) or [
            f"Documento interno de {pack.display_name} orientado a {pack.sector}.",
            f"Se revisaron temas de {', '.join(pack.topics[:2])} con el equipo responsable.",
        ], n=min(3, max(1, len(pack.filler_paragraphs) or 2))))
        # deterministic extra sentences from pack
        if pack.metrics:
            sections.append(f"Indicadores de referencia: {'; '.join(_pick(rng, pack.metrics, 2))}.")
        if pack.lexicon:
            sections.append(
                f"El lenguaje del documento usa términos de {pack.sector}: "
                f"{', '.join(_pick(rng, pack.lexicon, 3))}."
            )
    lines.append("")
    for para in sections:
        lines.append(para)
        lines.append("")


def build_document(
    record: dict[str, Any],
    rng: random.Random,
    *,
    body_sections: list[str] | None = None,
    variant: str | None = None,
) -> tuple[str, list[dict[str, Any]], bytes | None, str]:
    """Return (canonical_text, spans, raw_override, variant_name)."""
    template = record["template"]
    path = record["path"]
    label = record["label"]
    fp_traps = list(record.get("fp_traps") or [])
    expected = list(record.get("expected_spans") or [])

    person = person_for_record(rng, path)
    filled = fill_span_values(expected, person, rng) if expected else []
    pack = content_pack_for(path)
    chosen = variant or choose_variant(template, rng)

    if template == "corrupt_seed":
        raw = bytes(rng.getrandbits(8) for _ in range(256))
        raw = b"\xff\xfe" + raw + b"\x00\x01\x02"
        return "", [], raw, "corrupt"

    builders = {
        "boletin_catalogo": _boletin,
        "procedimiento_ops": _procedimiento,
        "informe_proyecto": _informe,
        "nota_rrhh": _nota_rrhh,
        "factura_liquidacion": _factura,
        "contrato_extracto": _contrato,
        "client_contact_list": _client_contacts,
    }
    if template not in builders:
        raise ValueError(f"unknown template: {template}")

    canonical, variant_out = builders[template](
        path=path,
        person=person,
        filled=filled,
        fp_traps=fp_traps,
        label=label,
        rng=rng,
        fmt=record["format"],
        pack=pack,
        body_sections=body_sections,
        variant=chosen,
    )

    if filled:
        missing = [s for s in filled if s["text"] not in canonical]
        if missing:
            extra_lines = ensure_all_span_texts([], missing)
            canonical = canonical.rstrip() + "\n" + "\n".join(extra_lines) + "\n"
        spans = locate_offsets(canonical, filled)
    else:
        spans = []

    if label == "limpio" and spans and template != "corrupt_seed":
        raise RuntimeError(f"{record['id']}: limpio produced spans")
    if label == "con_pii" and not spans:
        raise RuntimeError(f"{record['id']}: con_pii produced no spans")

    return canonical, spans, None, variant


def choose_variant(template: str, rng: random.Random) -> str:
    mapping = {
        "boletin_catalogo": _BOLETIN_VARIANTS,
        "informe_proyecto": _INFORME_VARIANTS,
        "procedimiento_ops": _PROC_VARIANTS,
        "nota_rrhh": _RRHH_VARIANTS,
        "factura_liquidacion": _FACTURA_VARIANTS,
        "contrato_extracto": _CONTRATO_VARIANTS,
        "client_contact_list": ("csv_roster",),
        "corrupt_seed": ("corrupt",),
    }
    return rng.choice(list(mapping.get(template, ("default",))))


def _boletin(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    if fmt == "csv":
        variant = "catalog"
    lines: list[str] = []

    if variant == "newsletter":
        lines.extend(
            [
                f"Andes Advisory S.A.C. — {title}",
                f"Boletín de difusión · {pack.display_name}",
                f"Edición de laboratorio · código {rng.choice(PROJECT_CODES)}",
                "",
                "En esta edición",
            ]
        )
        for t in _pick(rng, pack.topics, 3):
            lines.append(f"- {t}")
        lines.append("")
        lines.append("Destacados")
        for p in _pick(rng, pack.products, 3):
            lines.append(f"- {p}")
    elif variant == "faq":
        lines.extend(
            [
                f"Preguntas frecuentes — {title}",
                f"Ámbito: {pack.sector}",
                "",
                f"¿Qué servicios cubre {pack.display_name} en este material?",
                f"Principalmente {', '.join(_pick(rng, pack.products, 2))}.",
                "",
                "¿Cómo solicito más información?",
                "Escríbanos a comercial@andesadvisory.pe o use la mesa de ayuda publicada.",
                "",
                f"¿Qué indicadores se mencionan?",
                f"{'; '.join(_pick(rng, pack.metrics, 2))}.",
            ]
        )
    elif variant == "brochure":
        lines.extend(
            [
                f"Brochure — {title}",
                "Andes Advisory S.A.C. · Lima, Perú",
                "",
                f"Propuesta de valor para {pack.display_name}",
                f"Acompañamos iniciativas de {pack.sector} con foco en resultados medibles.",
                "",
                "Líneas de servicio",
            ]
        )
        for p in _pick(rng, pack.products, 4):
            lines.append(f"• {p}")
        lines.extend(["", "Léxico del sector", ", ".join(_pick(rng, pack.lexicon, 5))])
    elif variant == "press":
        lines.extend(
            [
                f"Nota de prensa — {title}",
                "Andes Advisory S.A.C.",
                f"Lima, {rng.choice(['marzo', 'abril', 'mayo'])} 2026",
                "",
                f"{pack.display_name} y Andes Advisory refuerzan colaboración en {pack.sector}.",
            ]
        )
    else:  # catalog
        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(["sku", "descripcion", "rubro", "nota"])
            for p in _pick(rng, pack.products, 8):
                w.writerow([make_sku(rng), p, pack.sector, rng.choice(pack.lexicon)])
            for _ in range(rng.randint(5, 12)):
                w.writerow(
                    [
                        make_sku(rng),
                        rng.choice(pack.products),
                        pack.sector,
                        rng.choice(pack.topics),
                    ]
                )
            text = buf.getvalue()
            # FP traps as CSV comment lines (still searchable for validators)
            trap_lines: list[str] = []
            _inject_fp_traps(trap_lines, fp_traps, rng)
            if trap_lines:
                text += "".join(f"# {ln}\n" for ln in trap_lines)
            return text, variant
        lines.extend(
            [
                f"Catálogo — {title}",
                f"Cliente de referencia: {pack.display_name}",
                "",
                "Ítems destacados",
            ]
        )
        for p in _pick(rng, pack.products, 5):
            lines.append(f"- {make_sku(rng)} · {p}")

    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines.extend(
        [
            "",
            "Contacto comercial (área, sin datos personales): comercial@andesadvisory.pe",
            "Lima, Perú",
        ]
    )
    if filled:
        lines.append("")
        lines.extend(embed_pii_block(filled, person, rng))
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _procedimiento(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    if variant not in _PROC_VARIANTS:
        variant = rng.choice(_PROC_VARIANTS)
    lines: list[str] = []

    if variant == "sop":
        lines.extend(
            [
                f"PROCEDIMIENTO INTERNO — {title}",
                f"{pack.display_name} · {pack.sector}",
                f"Código: SOP-{rng.randint(100, 999)} · Proyecto {rng.choice(PROJECT_CODES)}",
                "",
                "1. Objetivo",
                f"Estandarizar actividades de {pack.sector} asociadas a {title.lower()}.",
                "",
                "2. Alcance",
                f"Aplica a roles de {', '.join(_pick(rng, AREAS, 3))}.",
                "",
                "3. Pasos",
                "3.1 Verificar precondiciones del entorno y ventanas de cambio.",
                "3.2 Registrar la actividad en la bitácora operativa.",
                "3.3 Validar criterios de aceptación con el responsable del servicio.",
                "3.4 Notificar al canal de guardia si hay impacto en usuarios.",
                "",
                "4. Indicadores",
                f"- {_pick(rng, pack.metrics, 1)[0]}",
                f"- Riesgo relacionado: {rng.choice(RISK_IDS)}",
            ]
        )
    elif variant == "checklist":
        lines.extend(
            [
                f"CHECKLIST — {title}",
                pack.display_name,
                "",
                "Antes de ejecutar",
            ]
        )
        for t in _pick(rng, pack.topics, 4):
            lines.append(f"[ ] {t}")
        lines.extend(["", "Durante la ejecución"])
        for lex in _pick(rng, pack.lexicon, 4):
            lines.append(f"[ ] Revisar control de {lex}")
        lines.extend(["", "Cierre", "[ ] Actualizar bitácora", "[ ] Comunicar resultado"])
    elif variant == "runbook":
        lines.extend(
            [
                f"RUNBOOK — {title}",
                f"Servicio: {pack.display_name}",
                "",
                "Síntoma / disparador",
                f"Desviación en {_pick(rng, pack.metrics, 1)[0]} o alerta de {_pick(rng, pack.lexicon, 1)[0]}.",
                "",
                "Diagnóstico",
                "1. Confirmar alcance del incidente.",
                "2. Revisar cambios recientes en el inventario de activos.",
                "3. Contrastar con el plan de continuidad vigente.",
                "",
                "Mitigación",
                "Aplicar rollback si el cambio es reversible; escalar P1 al canal de guardia.",
                "",
                "Post-mortem",
                "Documentar causa raíz y acciones preventivas en el SOP de incidentes.",
            ]
        )
    else:  # politica
        lines.extend(
            [
                f"POLÍTICA / RESUMEN — {title}",
                "Andes Advisory S.A.C.",
                "",
                f"Esta política orienta el tratamiento de {pack.sector} en la firma.",
                f"Temas cubiertos: {', '.join(_pick(rng, pack.topics, 3))}.",
                "",
                "Principios",
                "- Minimización de datos personales en material operativo.",
                "- Segregación de duties entre operaciones y proyectos de cliente.",
                "- Registro de excepciones con aprobación del área responsable.",
            ]
        )

    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines.extend(["", "Fin del documento operativo."])
    if filled:
        lines.append("")
        lines.extend(embed_pii_block(filled, person, rng))
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _informe(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    if variant not in _INFORME_VARIANTS:
        variant = rng.choice(_INFORME_VARIANTS)
    code = next((c for c in PROJECT_CODES if c.lower() in path.lower()), rng.choice(PROJECT_CODES))
    lines: list[str] = [
        f"INFORME DE PROYECTO — {title}",
        f"Andes Advisory S.A.C. · {pack.display_name}",
        f"Código: {code} · Sector: {pack.sector}",
        "",
    ]

    if variant == "weekly":
        lines.extend(
            [
                "1. Resumen de la semana",
                f"Se avanzó en {', '.join(_pick(rng, pack.topics, 2))}.",
                "",
                "2. Indicadores",
            ]
        )
        for m in _pick(rng, pack.metrics, 3):
            lines.append(f"- {m}")
        lines.extend(
            [
                "",
                "3. Bloqueadores",
                f"- {rng.choice(RISK_IDS)}: requiere decisión de sponsor.",
                "",
                "4. Próximos pasos",
                f"- Cerrar entregable de {_pick(rng, pack.products, 1)[0]}",
                "- Actualizar registro de riesgos",
            ]
        )
    elif variant == "kickoff":
        lines.extend(
            [
                "1. Objetivos del kickoff",
                f"Alinear alcance de {pack.display_name} en {pack.sector}.",
                "",
                "2. Agenda",
            ]
        )
        for i, t in enumerate(_pick(rng, pack.topics, 4), 1):
            lines.append(f"{i}. {t}")
        lines.extend(
            [
                "",
                "3. Roles",
                f"- {_pick(rng, JOB_TITLES, 1)[0]} (Andes Advisory)",
                f"- Sponsor de negocio ({pack.display_name})",
                f"- {_pick(rng, JOB_TITLES, 1)[0]} (cliente)",
            ]
        )
    elif variant == "riesgos":
        lines.extend(["1. Registro narrativo de riesgos", ""])
        for rid in _pick(rng, RISK_IDS, 4):
            lines.append(f"{rid}")
            lines.append(
                f"  Impacto en {_pick(rng, pack.lexicon, 1)[0]}; "
                f"mitigación vía {_pick(rng, pack.products, 1)[0]}."
            )
            lines.append("")
    else:  # acta
        lines.extend(
            [
                "Acta de reunión",
                f"Fecha referencial: 2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                f"Participan equipos de {pack.display_name} y Andes Advisory.",
                "",
                "Acuerdos",
            ]
        )
        for t in _pick(rng, pack.topics, 3):
            lines.append(f"- Acuerdo sobre {t}")
        lines.extend(["", "Pendientes", f"- Seguimiento de {rng.choice(RISK_IDS)}"])

    _merge_body(lines, body_sections, pack, rng)

    if filled:
        lines.append("")
        lines.append("Contacto / stakeholder")
        lines.extend(embed_pii_block(filled, person, rng, styles=["ficha", "signature", "inline", "email_header"]))
    else:
        lines.extend(
            [
                "",
                "Roles (sin datos personales)",
                "- Sponsor de negocio",
                "- Líder técnico",
                "- Analista de calidad",
            ]
        )

    _inject_fp_traps(lines, fp_traps, rng)
    lines.extend(["", "Cierre", "Revisión de hitos y cierre de observaciones."])
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _nota_rrhh(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    vals = by_type(filled)
    if fmt == "csv" and filled:
        return _rrhh_csv(vals, person, rng), "csv_roster"

    if variant not in _RRHH_VARIANTS:
        variant = rng.choice(_RRHH_VARIANTS)
    lines = [
        f"RRHH — {title}",
        f"{pack.display_name}",
        "",
    ]
    if filled:
        if variant == "memo":
            lines.extend(
                [
                    "Memorando interno",
                    f"Asunto: actualización de ficha — {title}",
                    "",
                ]
            )
            lines.extend(embed_pii_block(filled, person, rng, styles=["email_header", "ficha"]))
        else:
            lines.append("Ficha / nota de colaborador")
            lines.extend(embed_pii_block(filled, person, rng, styles=["ficha", "signature"]))
        lines.append("")
        lines.append(f"Área sugerida: {rng.choice(AREAS)}")
        lines.append(f"Puesto referencial: {rng.choice(JOB_TITLES)}")
    else:
        lines.extend(
            [
                f"Documento de {variant} interna.",
                "No incluye datos personales de colaboradores.",
                f"Temas: {', '.join(_pick(rng, pack.topics, 3))}.",
            ]
        )
    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _rrhh_csv(vals: dict[str, str], person: Person, rng: random.Random) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["nombre", "apellido", "dni", "correo", "telefono", "area", "puesto"])
    writer.writerow(
        [
            vals.get("given_name", person.given_name),
            vals.get("surname", person.surname),
            vals.get("id_card_number", person.id_card_number),
            vals.get("email_address", person.email_address),
            vals.get("phone_number", person.phone_number),
            rng.choice(AREAS),
            rng.choice(JOB_TITLES),
        ]
    )
    for _ in range(rng.randint(8, 18)):
        extra = make_person(rng, domain="andesadvisory.pe")
        writer.writerow(
            [
                extra.given_name,
                extra.surname,
                extra.id_card_number,
                extra.email_address,
                extra.phone_number,
                rng.choice(AREAS),
                rng.choice(JOB_TITLES),
            ]
        )
    return buf.getvalue()


def _factura(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    vals = by_type(filled)
    if variant not in _FACTURA_VARIANTS:
        variant = rng.choice(_FACTURA_VARIANTS)

    if fmt == "csv" and filled:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["ruc", "cci", "correo", "telefono", "monto_pen", "concepto", "proyecto"])
        w.writerow(
            [
                vals.get("organization_tax_id", person.organization_tax_id),
                vals.get("bank_account", person.bank_account),
                vals.get("email_address", person.email_address),
                vals.get("phone_number", person.phone_number),
                f"{rng.randint(500, 9000)}.00",
                rng.choice(INVOICE_CONCEPTS),
                rng.choice(PROJECT_CODES),
            ]
        )
        for _ in range(rng.randint(3, 8)):
            w.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    f"{rng.randint(200, 4000)}.00",
                    rng.choice(INVOICE_CONCEPTS),
                    rng.choice(PROJECT_CODES),
                ]
            )
        return buf.getvalue(), "csv_lines"

    lines = [
        f"COMPROBANTE / LIQUIDACIÓN — {title}",
        f"Andes Advisory S.A.C. · {pack.display_name}",
        f"Variante: {variant} · Moneda: PEN · N° interno: F-{rng.randint(1000, 9999)}",
        "",
        "Detalle de conceptos",
    ]
    for c in _pick(rng, INVOICE_CONCEPTS, 3):
        lines.append(f"- {c}: S/ {rng.randint(800, 12000)}.00")
    lines.append(f"Importe referencial total: S/ {rng.randint(3000, 35000)}.00")
    lines.append("")

    if filled:
        lines.append("Datos de facturación / cobranzas")
        lines.extend(embed_pii_block(filled, person, rng, styles=["ficha", "signature", "inline"]))
    else:
        lines.append("Resumen presupuestal sin datos de contacto personal.")

    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _contrato(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    title = _title_from_path(path)
    vals = by_type(filled)
    if variant not in _CONTRATO_VARIANTS:
        variant = rng.choice(_CONTRATO_VARIANTS)
    lines = [
        f"EXTRACTO CONTRACTUAL / NDA — {title}",
        f"Andes Advisory S.A.C. · Legal · {pack.display_name}",
        f"Variante: {variant}",
        "",
    ]

    if variant == "checklist_legal":
        lines.extend(
            [
                "Checklist de revisión",
                "[ ] Identificación de partes",
                "[ ] Cláusula de confidencialidad",
                "[ ] Plazo y terminación",
                "[ ] Ley aplicable (Perú)",
                "",
            ]
        )
    elif variant == "clausulas":
        lines.extend(
            [
                "Cláusula 4 — Confidencialidad",
                "La información intercambiada se mantiene bajo deber de reserva.",
                "",
                "Cláusula 5 — Uso permitido",
                f"Uso limitado a actividades de {pack.sector}.",
                "",
            ]
        )
    else:
        lines.append("Cláusula de identificación de las partes")

    if filled:
        # Prefer inline/contrato style so PII sits in prose
        lines.extend(embed_pii_block(filled, person, rng, styles=["inline", "ficha"]))
        lines.append("declara haber leído las obligaciones de confidencialidad.")
    else:
        lines.append("Extracto genérico sin datos personales de las partes.")

    lines.extend(
        [
            "",
            "Cláusula de confidencialidad",
            "La información intercambiada se mantiene bajo deber de reserva durante y "
            "después de la vigencia del encargo.",
            "",
            f"Referencias de proyecto: {rng.choice(PROJECT_CODES)}; riesgo {rng.choice(RISK_IDS)}.",
        ]
    )
    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", variant


def _client_contacts(
    *,
    path: str,
    person: Person,
    filled: list[dict[str, str]],
    fp_traps: list[str],
    label: str,
    rng: random.Random,
    fmt: str,
    pack: ContentPack,
    body_sections: list[str] | None,
    variant: str,
) -> tuple[str, str]:
    vals = by_type(filled)
    headers = [
        "nombre",
        "dni",
        "correo",
        "telefono",
        "direccion",
        "celular",
        "cuenta_banco",
        "consumo_mensual",
    ]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(headers)
        # Primary row carries expected spans
        primary_name = f"{vals.get('given_name', person.given_name)} {vals.get('surname', person.surname)}"
        w.writerow(
            [
                primary_name if "given_name" in vals or "surname" in vals else person.full_name,
                vals.get("id_card_number", person.id_card_number),
                vals.get("email_address", person.email_address),
                vals.get("phone_number", person.phone_number),
                vals.get("street", person.street),
                vals.get("phone_number", person.phone_number),
                vals.get("bank_account", person.bank_account),
                f"{rng.randint(80, 900)}.00",
            ]
        )
        # Ensure given_name and surname appear as exact tokens for offsets:
        # primary_name contains both with a space — find works for each substring.
        domain = pack.slug.replace("_", "") + ".pe" if pack.slug in (
            "banco_andino", "retail_pacifico", "minera_sierra", "clinica_salud_lima", "agro_valle"
        ) else None
        domain_map = {
            "banco_andino": "bancoandino.pe",
            "retail_pacifico": "retailpacifico.pe",
            "minera_sierra": "minerasierra.pe",
            "clinica_salud_lima": "clinicasaludlima.pe",
            "agro_valle": "agrovalle.pe",
        }
        dom = domain_map.get(pack.slug)
        for _ in range(rng.randint(12, 28)):
            extra = make_person(rng, domain=dom)
            w.writerow(
                [
                    extra.full_name,
                    extra.id_card_number,
                    extra.email_address,
                    extra.phone_number,
                    extra.street,
                    extra.phone_number,
                    extra.bank_account,
                    f"{rng.randint(50, 1200)}.00",
                ]
            )
        text = buf.getvalue()
        # If given_name/surname must appear and full_name concatenation is fine for find()
        if filled:
            # Force exact presence for types that might not be in CSV columns alone
            # city/postal etc. rare in this template — ensure_via rewrite if needed
            missing = [s for s in filled if s["text"] not in text]
            if missing:
                # Add a comment row-like trailer as text lines (still part of file)
                extra_lines = ["# " + ", ".join(f"{s['type']}={s['text']}" for s in missing)]
                text = text + "\n".join(extra_lines) + "\n"
        return text, "csv_roster"

    lines = [
        f"Lista de contactos — {pack.display_name}",
        f"Sector: {pack.sector}",
        "",
    ]
    if filled:
        lines.extend(embed_pii_block(filled, person, rng))
    _merge_body(lines, body_sections, pack, rng)
    _inject_fp_traps(lines, fp_traps, rng)
    lines = ensure_all_span_texts(lines, filled)
    return "\n".join(lines).rstrip() + "\n", "narrative"
