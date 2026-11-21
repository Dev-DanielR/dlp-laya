"""One-shot builder for data/manifest.json. Run from repo root."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "manifest.json"

records: list[dict] = []


def add(
    id_: str,
    path: str,
    fmt: str,
    label: str,
    template: str,
    *,
    case_tags: list[str] | None = None,
    spans: list[dict] | None = None,
    fp_traps: list[str] | None = None,
    notes: str = "",
) -> None:
    rel = path.replace("\\", "/")
    acl = "/files/" + "/".join(rel.split("/")[:-1])
    if acl.endswith("/"):
        acl = acl[:-1]
    records.append(
        {
            "id": id_,
            "path": rel,
            "format": fmt,
            "label": label,
            "template": template,
            "case_tags": case_tags or ["caso03"],
            "acl_hint_path": acl,
            "expected_spans": spans or [],
            "fp_traps": fp_traps or [],
            "notes": notes,
        }
    )


# --- publico/ : 35 limpio, FP traps on a subset ---
pub_items = [
    ("pub-001", "publico/catalogo_servicios.pdf", "pdf", "boletin_catalogo", ["sku_8dig", "proyeccion"], "Catálogo comercial con SKU 8 dígitos"),
    ("pub-002", "publico/boletin_empresa.pdf", "pdf", "boletin_catalogo", ["hotline", "confidencialidad"], "Boletín con hotline 01-615-8000"),
    ("pub-003", "publico/catalogo_publico.txt", "txt", "boletin_catalogo", ["sku_8dig", "proyeccion"], "CASO 05 named fixture style"),
    ("pub-004", "publico/faq_atencion_cliente.txt", "txt", "boletin_catalogo", ["hotline"], ""),
    ("pub-005", "publico/codigo_etica.pdf", "pdf", "procedimiento_ops", ["confidencialidad"], ""),
    ("pub-006", "publico/brochure_transformacion.docx", "docx", "boletin_catalogo", ["proyeccion"], ""),
    ("pub-007", "publico/lista_sku_q1.csv", "csv", "boletin_catalogo", ["sku_8dig"], "Solo códigos de producto"),
    ("pub-008", "publico/prensa_apertura_oficina.txt", "txt", "boletin_catalogo", [], ""),
    ("pub-009", "publico/calendario_capacitaciones.pdf", "pdf", "boletin_catalogo", [], ""),
    ("pub-010", "publico/politica_privacidad_resumen.txt", "txt", "procedimiento_ops", ["confidencialidad", "dni_mention"], "Menciona DNI sin número"),
    ("pub-011", "publico/case_study_anonimo.pdf", "pdf", "informe_proyecto", ["proyeccion"], "Caso anonimizado de marketing"),
    ("pub-012", "publico/tarifario_servicios.xlsx.txt", "txt", "boletin_catalogo", ["sku_8dig"], ""),
    ("pub-013", "publico/guia_onboarding_cliente.pdf", "pdf", "procedimiento_ops", [], ""),
    ("pub-014", "publico/infografia_metodologia.docx", "docx", "boletin_catalogo", [], ""),
    ("pub-015", "publico/newsletter_marzo.txt", "txt", "boletin_catalogo", ["hotline", "proyeccion"], ""),
    ("pub-016", "publico/newsletter_abril.txt", "txt", "boletin_catalogo", ["sku_8dig"], ""),
    ("pub-017", "publico/glosario_digital.pdf", "pdf", "boletin_catalogo", [], ""),
    ("pub-018", "publico/rueda_prensa_2026.txt", "txt", "boletin_catalogo", [], ""),
    ("pub-019", "publico/alianza_academica.pdf", "pdf", "boletin_catalogo", [], ""),
    ("pub-020", "publico/ficha_servicio_data.pdf", "pdf", "boletin_catalogo", ["proyeccion"], ""),
    ("pub-021", "publico/ficha_servicio_cyber.docx", "docx", "boletin_catalogo", ["confidencialidad"], ""),
    ("pub-022", "publico/faq_facturacion.txt", "txt", "boletin_catalogo", ["hotline"], ""),
    ("pub-023", "publico/mapa_oficinas.txt", "txt", "boletin_catalogo", [], "Solo distritos, sin calles personales"),
    ("pub-024", "publico/requisitos_rfp_publico.pdf", "pdf", "boletin_catalogo", [], ""),
    ("pub-025", "publico/plantilla_propuesta_vacia.docx", "docx", "boletin_catalogo", [], ""),
    ("pub-026", "publico/indicadores_mercado_abierto.pdf", "pdf", "informe_proyecto", ["proyeccion"], ""),
    ("pub-027", "publico/encuesta_satisfaccion_form.txt", "txt", "boletin_catalogo", [], "Formulario vacío"),
    ("pub-028", "publico/aviso_mantenimiento_web.txt", "txt", "boletin_catalogo", ["hotline"], ""),
    ("pub-029", "publico/catalogo_cursos_abiertos.csv", "csv", "boletin_catalogo", ["sku_8dig"], ""),
    ("pub-030", "publico/manifiesto_sostenibilidad.pdf", "pdf", "boletin_catalogo", [], ""),
    ("pub-031", "publico/terminos_uso_portal.txt", "txt", "procedimiento_ops", ["confidencialidad"], ""),
    ("pub-032", "publico/kit_prensa.zip.txt", "txt", "boletin_catalogo", [], "Índice de assets públicos"),
    ("pub-033", "publico/comparativo_planes.pdf", "pdf", "boletin_catalogo", ["sku_8dig"], ""),
    ("pub-034", "publico/webinar_resumen.docx", "docx", "boletin_catalogo", ["proyeccion"], ""),
    ("pub-035", "publico/directorio_areas_publico.txt", "txt", "boletin_catalogo", ["hotline"], "Solo áreas y anexos corporativos"),
]
for id_, path, fmt, tmpl, traps, notes in pub_items:
    tags = ["caso03", "caso05"]
    add(id_, path, fmt, "limpio", tmpl, case_tags=tags, fp_traps=traps, notes=notes)

# --- interno/rrhh : 8 files, 5 PII ---
rrhh = [
    ("rrhh-001", "interno/rrhh/ficha_alta_colaborador.txt", "txt", "con_pii", "nota_rrhh", True),
    ("rrhh-002", "interno/rrhh/planilla_parcial_marzo.csv", "csv", "con_pii", "nota_rrhh", True),
    ("rrhh-003", "interno/rrhh/solicitud_vacaciones.docx", "docx", "con_pii", "nota_rrhh", True),
    ("rrhh-004", "interno/rrhh/evaluacion_desempeno.pdf", "pdf", "con_pii", "nota_rrhh", True),
    ("rrhh-005", "interno/rrhh/contacto_emergencia.txt", "txt", "con_pii", "nota_rrhh", True),
    ("rrhh-006", "interno/rrhh/politica_teletrabajo.pdf", "pdf", "limpio", "procedimiento_ops", False),
    ("rrhh-007", "interno/rrhh/organigrama_areas.txt", "txt", "limpio", "procedimiento_ops", False),
    ("rrhh-008", "interno/rrhh/calendario_feriados_2026.txt", "txt", "limpio", "procedimiento_ops", False),
]
for id_, path, fmt, label, tmpl, has_pii in rrhh:
    spans = (
        [
            {"type": "given_name", "text": "PLACEHOLDER"},
            {"type": "surname", "text": "PLACEHOLDER"},
            {"type": "id_card_number", "text": "PLACEHOLDER"},
            {"type": "email_address", "text": "PLACEHOLDER"},
            {"type": "phone_number", "text": "PLACEHOLDER"},
        ]
        if has_pii
        else []
    )
    add(id_, path, fmt, label, tmpl, spans=spans, notes="RRHH" + (" PII" if has_pii else " limpio"))

# --- interno/finanzas : 8 files, 3 PII ---
fin = [
    ("fin-001", "interno/finanzas/factura_00123.txt", "txt", "con_pii", "factura_liquidacion", True),
    ("fin-002", "interno/finanzas/liquidacion_proveedor.csv", "csv", "con_pii", "factura_liquidacion", True),
    ("fin-003", "interno/finanzas/cci_cobranzas.txt", "txt", "con_pii", "factura_liquidacion", True),
    ("fin-004", "interno/finanzas/presupuesto_anual_resumen.pdf", "pdf", "limpio", "informe_proyecto", False),
    ("fin-005", "interno/finanzas/politica_gastos.docx", "docx", "limpio", "procedimiento_ops", False),
    ("fin-006", "interno/finanzas/calendario_cierre.txt", "txt", "limpio", "procedimiento_ops", False),
    ("fin-007", "interno/finanzas/indicadores_margen.pdf", "pdf", "limpio", "informe_proyecto", False),
    ("fin-008", "interno/finanzas/plantilla_orden_compra.txt", "txt", "limpio", "boletin_catalogo", False),
]
for id_, path, fmt, label, tmpl, has_pii in fin:
    spans = (
        [
            {"type": "organization_tax_id", "text": "PLACEHOLDER"},
            {"type": "bank_account", "text": "PLACEHOLDER"},
            {"type": "email_address", "text": "PLACEHOLDER"},
            {"type": "phone_number", "text": "PLACEHOLDER"},
        ]
        if has_pii
        else []
    )
    add(id_, path, fmt, label, tmpl, spans=spans)

# --- interno/legal : 6 files, 2 PII ---
leg = [
    ("leg-001", "interno/legal/nda_extracto_modelo.docx", "docx", "con_pii", "contrato_extracto", True),
    ("leg-002", "interno/legal/contrato_marco_extracto.pdf", "pdf", "con_pii", "contrato_extracto", True),
    ("leg-003", "interno/legal/politica_retencion.txt", "txt", "limpio", "procedimiento_ops", False),
    ("leg-004", "interno/legal/checklist_compliance.pdf", "pdf", "limpio", "procedimiento_ops", False),
    ("leg-005", "interno/legal/matriz_riesgos_legal.txt", "txt", "limpio", "informe_proyecto", False),
    ("leg-006", "interno/legal/guia_firmas.docx", "docx", "limpio", "procedimiento_ops", False),
]
for id_, path, fmt, label, tmpl, has_pii in leg:
    spans = (
        [
            {"type": "given_name", "text": "PLACEHOLDER"},
            {"type": "surname", "text": "PLACEHOLDER"},
            {"type": "id_card_number", "text": "PLACEHOLDER"},
            {"type": "organization_tax_id", "text": "PLACEHOLDER"},
            {"type": "street", "text": "PLACEHOLDER"},
            {"type": "city", "text": "PLACEHOLDER"},
            {"type": "email_address", "text": "PLACEHOLDER"},
        ]
        if has_pii
        else []
    )
    add(id_, path, fmt, label, tmpl, spans=spans)

# --- interno/ops : 8 limpio ---
ops = [
    ("ops-001", "interno/ops/sop_backup.txt", "txt"),
    ("ops-002", "interno/ops/sop_incidentes.pdf", "pdf"),
    ("ops-003", "interno/ops/runbook_netbird.docx", "docx"),
    ("ops-004", "interno/ops/inventario_activos.csv", "csv"),
    ("ops-005", "interno/ops/plan_continuidad.pdf", "pdf"),
    ("ops-006", "interno/ops/checklist_despliegue.txt", "txt"),
    ("ops-007", "interno/ops/politica_accesos.txt", "txt"),
    ("ops-008", "interno/ops/diagrama_red_lab.txt", "txt"),
]
for id_, path, fmt in ops:
    fp = ["confidencialidad"] if id_ in ("ops-005", "ops-007") else []
    add(id_, path, fmt, "limpio", "procedimiento_ops", fp_traps=fp, case_tags=["caso03", "caso05"])

# --- clientes : 20 files, 5 PII ---
# 5 clients × (2 entregables limpios + structure); concentrate PII in confidencial/
clients = [
    ("banco_andino", "ba"),
    ("retail_pacifico", "rp"),
    ("minera_sierra", "ms"),
    ("clinica_salud_lima", "cs"),
    ("agro_valle", "av"),
]
cli_n = 0
pii_budget = {
    "banco_andino": True,  # confidencial list
    "retail_pacifico": True,
    "minera_sierra": True,
    "clinica_salud_lima": True,
    "agro_valle": True,
}
for cname, abbr in clients:
    cli_n += 1
    add(
        f"cli-{abbr}-001",
        f"clientes/{cname}/entregables/informe_avance.pdf",
        "pdf",
        "limpio",
        "informe_proyecto",
        notes="Entregable sin contactos personales",
    )
    cli_n += 1
    add(
        f"cli-{abbr}-002",
        f"clientes/{cname}/entregables/acta_reunion.txt",
        "txt",
        "limpio",
        "informe_proyecto",
        notes="Acta con roles, sin PII",
    )
    cli_n += 1
    add(
        f"cli-{abbr}-003",
        f"clientes/{cname}/entregables/roadmap.pptx.txt",
        "txt",
        "limpio",
        "boletin_catalogo",
        fp_traps=["proyeccion"],
    )
    # one confidencial PII per client = 5
    cli_n += 1
    fmt = "csv" if cname == "banco_andino" else ("docx" if cname in ("retail_pacifico", "agro_valle") else "txt")
    add(
        f"cli-{abbr}-004",
        f"clientes/{cname}/confidencial/contactos_proyecto.{fmt}",
        fmt,
        "con_pii",
        "client_contact_list" if fmt == "csv" else "informe_proyecto",
        spans=[
            {"type": "given_name", "text": "PLACEHOLDER"},
            {"type": "surname", "text": "PLACEHOLDER"},
            {"type": "email_address", "text": "PLACEHOLDER"},
            {"type": "phone_number", "text": "PLACEHOLDER"},
            {"type": "id_card_number", "text": "PLACEHOLDER"},
        ],
        notes=f"PII contactos {cname}",
    )

assert cli_n == 20, cli_n

# --- proyectos : 12 files, 2 PII ---
proys = [
    ("P2026-014_transformacion_digital", "p014"),
    ("P2026-021_due_diligence", "p021"),
    ("P2026-033_optimizacion_cadena", "p033"),
]
# 4 files each = 12; mark 2 as PII (one in 014, one in 021)
pii_paths = {
    ("P2026-014_transformacion_digital", 4),
    ("P2026-021_due_diligence", 3),
}
for pname, abbr in proys:
    for i, (suffix, fmt, tmpl) in enumerate(
        [
            ("kickoff_notas.txt", "txt", "informe_proyecto"),
            ("estado_semanal.pdf", "pdf", "informe_proyecto"),
            ("riesgos_registro.csv", "csv", "informe_proyecto"),
            ("anexo_stakeholders.docx", "docx", "informe_proyecto"),
        ],
        start=1,
    ):
        is_pii = (pname, i) in pii_paths
        spans = (
            [
                {"type": "given_name", "text": "PLACEHOLDER"},
                {"type": "surname", "text": "PLACEHOLDER"},
                {"type": "email_address", "text": "PLACEHOLDER"},
                {"type": "phone_number", "text": "PLACEHOLDER"},
            ]
            if is_pii
            else []
        )
        add(
            f"prj-{abbr}-{i:03d}",
            f"proyectos/{pname}/{suffix}",
            fmt,
            "con_pii" if is_pii else "limpio",
            tmpl,
            spans=spans,
            fp_traps=["proyeccion"] if not is_pii and i == 2 else [],
            case_tags=["caso03", "caso05"] if not is_pii else ["caso03"],
        )

# --- casos/ : 4 files, 3 PII + 1 corrupt ---
add(
    "caso-001",
    "casos/caso01_informe_sensible.docx",
    "docx",
    "con_pii",
    "informe_proyecto",
    case_tags=["caso01", "caso03"],
    spans=[
        {"type": "given_name", "text": "PLACEHOLDER"},
        {"type": "surname", "text": "PLACEHOLDER"},
        {"type": "id_card_number", "text": "PLACEHOLDER"},
        {"type": "email_address", "text": "PLACEHOLDER"},
        {"type": "bank_account", "text": "PLACEHOLDER"},
        {"type": "credit_card_number", "text": "PLACEHOLDER"},
    ],
    notes="CASO 01: PII denso; ACL baja en esta ruta → denegado",
)
add(
    "caso-002",
    "casos/caso02_clientes_demo.csv",
    "csv",
    "con_pii",
    "client_contact_list",
    case_tags=["caso02", "caso03"],
    spans=[
        {"type": "given_name", "text": "PLACEHOLDER"},
        {"type": "surname", "text": "PLACEHOLDER"},
        {"type": "id_card_number", "text": "PLACEHOLDER"},
        {"type": "email_address", "text": "PLACEHOLDER"},
        {"type": "phone_number", "text": "PLACEHOLDER"},
        {"type": "street", "text": "PLACEHOLDER"},
        {"type": "city", "text": "PLACEHOLDER"},
        {"type": "bank_account", "text": "PLACEHOLDER"},
    ],
    notes="CASO 02: columnas nombre,dni,correo,telefono,direccion,celular,cuenta_banco,consumo_mensual",
)
add(
    "caso-004",
    "casos/caso04_proyecto_mixto.pdf",
    "pdf",
    "con_pii",
    "informe_proyecto",
    case_tags=["caso04", "caso03"],
    spans=[
        {"type": "given_name", "text": "PLACEHOLDER"},
        {"type": "surname", "text": "PLACEHOLDER"},
        {"type": "email_address", "text": "PLACEHOLDER"},
        {"type": "phone_number", "text": "PLACEHOLDER"},
        {"type": "organization_tax_id", "text": "PLACEHOLDER"},
    ],
    notes="CASO 04: mismo archivo bajo alta/media/baja",
)
add(
    "caso-005c",
    "casos/caso05_corrupto.bin",
    "bin",
    "limpio",
    "corrupt_seed",
    case_tags=["caso05", "caso03"],
    notes="Ilegible: error de lectura, no PII",
)

# --- summary checks ---
n = len(records)
n_pii = sum(1 for r in records if r["label"] == "con_pii")
n_clean = n - n_pii
assert 95 <= n <= 110, n
assert 18 <= n_pii <= 22, n_pii
ids = [r["id"] for r in records]
assert len(ids) == len(set(ids)), "duplicate ids"
paths = [r["path"] for r in records]
assert len(paths) == len(set(paths)), "duplicate paths"

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps(
        {
            "corpus": "andes-advisory-sac",
            "seed_default": 20261114,
            "version": 1,
            "counts": {"total": n, "con_pii": n_pii, "limpio": n_clean},
            "files": records,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"Wrote {OUT} total={n} con_pii={n_pii} limpio={n_clean}")
