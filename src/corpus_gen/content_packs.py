"""Path-conditioned lexicon packs for realistic document bodies."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentPack:
    slug: str
    display_name: str
    sector: str
    lexicon: tuple[str, ...]
    metrics: tuple[str, ...]
    topics: tuple[str, ...]
    products: tuple[str, ...]
    filler_paragraphs: tuple[str, ...] = field(default_factory=tuple)


_PUBLICO = ContentPack(
    slug="publico",
    display_name="Andes Advisory S.A.C.",
    sector="marketing y difusión",
    lexicon=(
        "transformación digital", "gobierno de datos", "experiencia del cliente",
        "ciberseguridad aplicada", "capacitación abierta", "metodología ágil",
    ),
    metrics=(
        "NPS referencial 62", "tiempo medio de onboarding 12 días",
        "+18% adopción de canales digitales en pilotos",
    ),
    topics=(
        "lanzamiento de catálogo Q2", "webinar de controles de acceso",
        "alianza académica con universidades limeñas",
    ),
    products=(
        "Diagnóstico de madurez digital", "Programa de gobierno de datos",
        "Paquete ciberseguridad esencial", "Optimización de cadena",
    ),
    filler_paragraphs=(
        "Andes Advisory publica materiales de difusión sin datos personales de clientes.",
        "Las cifras mostradas son ilustrativas y corresponden a escenarios de laboratorio.",
        "Para mayor información comercial escriba a comercial@andesadvisory.pe.",
    ),
)

_RRHH = ContentPack(
    slug="interno_rrhh",
    display_name="Andes Advisory · RRHH",
    sector="recursos humanos",
    lexicon=(
        "alta de colaborador", "evaluación de desempeño", "teletrabajo",
        "calendario de feriados", "planilla", "contacto de emergencia",
    ),
    metrics=("dotación activa 84", "rotación anual 9%", "vacantes abiertas 3"),
    topics=(
        "ciclo de evaluaciones Q1", "actualización de política de vacaciones",
        "inducción de nuevos ingresos",
    ),
    products=("Ficha de alta", "Solicitud de vacaciones", "Política de teletrabajo"),
    filler_paragraphs=(
        "Los formularios de RRHH siguen el formato interno de Andes Advisory.",
        "La información de colaboradores se trata conforme a la política de retención.",
    ),
)

_FINANZAS = ContentPack(
    slug="interno_finanzas",
    display_name="Andes Advisory · Finanzas",
    sector="finanzas y cobranzas",
    lexicon=(
        "liquidación de proveedor", "CCI de cobranzas", "margen operativo",
        "presupuesto anual", "orden de compra", "cierre contable",
    ),
    metrics=("margen bruto 34%", "DSO 41 días", "variación presupuesto -2.1%"),
    topics=("cierre de marzo", "conciliación de facturas", "forecast de caja"),
    products=("Factura de servicios", "Liquidación parcial", "Plantilla OC"),
    filler_paragraphs=(
        "Los montos están expresados en soles salvo indicación contraria.",
        "Toda liquidación debe referenciar el código de proyecto asociado.",
    ),
)

_LEGAL = ContentPack(
    slug="interno_legal",
    display_name="Andes Advisory · Legal",
    sector="legal y cumplimiento",
    lexicon=(
        "NDA", "retención documental", "matriz de riesgos", "compliance",
        "cláusula de confidencialidad", "firma electrónica",
    ),
    metrics=("contratos vigentes 27", "NDA activos 41", "hallazgos abiertos 2"),
    topics=("revisión de modelo NDA", "checklist de compliance", "política de firmas"),
    products=("Extracto contractual", "Guía de firmas", "Checklist compliance"),
    filler_paragraphs=(
        "Este extracto no sustituye el contrato completo firmado por las partes.",
        "Las obligaciones de reserva se mantienen durante la vigencia del encargo.",
    ),
)

_OPS = ContentPack(
    slug="interno_ops",
    display_name="Andes Advisory · Operaciones",
    sector="operaciones y soporte",
    lexicon=(
        "runbook", "bitácora operativa", "inventario de activos", "SOP",
        "plan de continuidad", "despliegue controlado",
    ),
    metrics=("MTTR 2.4 h", "disponibilidad 99.5%", "cambios del mes 11"),
    topics=("checklist de despliegue", "soporte Netbird", "backup semanal"),
    products=("Runbook de red", "SOP de incidentes", "Plan de continuidad"),
    filler_paragraphs=(
        "Antes de ejecutar un cambio, verificar ventana de mantenimiento y rollback.",
        "Los incidentes P1 se escalan al canal de guardia en menos de 15 minutos.",
    ),
)

_CLIENTS: dict[str, ContentPack] = {
    "banco_andino": ContentPack(
        slug="banco_andino",
        display_name="Banco Andino",
        sector="banca y servicios financieros",
        lexicon=(
            "onboarding digital", "canales móviles", "riesgo operativo",
            "core bancario", "KYC simplificado", "conciliación diaria",
        ),
        metrics=("adopción app +22%", "tickets fraude -8%", "SLA canales 98%"),
        topics=("piloto de autenticación", "tablero de riesgo", "migración de reportes"),
        products=("Informe de avance", "Acta de reunión", "Contactos del proyecto"),
        filler_paragraphs=(
            "El patrocinador de negocio validó el alcance del sprint de controles.",
            "Se priorizan entregables que reduzcan fricción en apertura de cuentas.",
        ),
    ),
    "retail_pacifico": ContentPack(
        slug="retail_pacifico",
        display_name="Retail Pacífico",
        sector="retail y omnicanalidad",
        lexicon=(
            "surtido", "sell-out", "omnicanal", "inventario en tienda",
            "promociones regionales", "última milla",
        ),
        metrics=("quiebre de stock 3.1%", "ticket promedio S/ 86", "fill-rate 94%"),
        topics=("sincronización e-commerce", "planograma Q2", "forecast de demanda"),
        products=("Roadmap comercial", "Informe de avance", "Acta de reunión"),
        filler_paragraphs=(
            "Las tiendas piloto en Lima moderna reportaron mejor visibilidad de stock.",
            "Se acordó revisar el surtido estacional antes del feriado largo.",
        ),
    ),
    "minera_sierra": ContentPack(
        slug="minera_sierra",
        display_name="Minera Sierra",
        sector="minería y operaciones de campo",
        lexicon=(
            "seguridad industrial", "turno de planta", "cadena de suministro",
            "permisos ambientales", "mantenimiento predictivo", "campamento",
        ),
        metrics=("disponibilidad de flota 91%", "incidentes perdidos 0", "OTIF 88%"),
        topics=("optimización de logística", "tablero de seguridad", "contratos EPC"),
        products=("Informe de avance", "Registro de riesgos", "Contactos del proyecto"),
        filler_paragraphs=(
            "El comité de seguridad revisó indicadores de la quincena en planta.",
            "La continuidad de proveedores críticos se mantiene en seguimiento semanal.",
        ),
    ),
    "clinica_salud_lima": ContentPack(
        slug="clinica_salud_lima",
        display_name="Clínica Salud Lima",
        sector="salud privada",
        lexicon=(
            "historia clínica electrónica", "citas ambulatorias", "facturación EPS",
            "privacidad de pacientes", "indicadores de calidad", "admisión",
        ),
        metrics=("ocupación camas 78%", "espera media 19 min", "satisfacción 4.3/5"),
        topics=("integración HIS", "tablero de calidad", "protocolo de alta"),
        products=("Informe de avance", "Acta de reunión", "Contactos del proyecto"),
        filler_paragraphs=(
            "El piloto de agenda ambulatoria redujo reprogramaciones en dos sedes.",
            "Se refuerza el tratamiento de datos clínicos conforme a política interna.",
        ),
    ),
    "agro_valle": ContentPack(
        slug="agro_valle",
        display_name="Agro Valle",
        sector="agroindustria",
        lexicon=(
            "cosecha", "trazabilidad", "exportación", "cadena de frío",
            "certificación", "rendimiento por hectárea",
        ),
        metrics=("rendimiento +6%", "merma postcosecha 4%", "OTIF exportación 92%"),
        topics=("trazabilidad de lote", "plan de exportación", "calidad de empaque"),
        products=("Informe de avance", "Roadmap de temporada", "Contactos del proyecto"),
        filler_paragraphs=(
            "La ventana de cosecha exige sincronizar transporte y packing diariamente.",
            "Los lotes de exportación mantienen registro de temperatura extremo a extremo.",
        ),
    ),
}

_PROJECTS: dict[str, ContentPack] = {
    "P2026-014": ContentPack(
        slug="P2026-014",
        display_name="P2026-014 Transformación digital",
        sector="transformación digital",
        lexicon=(
            "roadmap digital", "casos de uso", "gobierno del cambio",
            "quick wins", "arquitectura objetivo",
        ),
        metrics=("casos priorizados 9", "quick wins cerrados 3", "adopción piloto 41%"),
        topics=("kickoff con sponsors", "mapa de stakeholders", "riesgos de adopción"),
        products=("Estado semanal", "Anexo de stakeholders", "Registro de riesgos"),
        filler_paragraphs=(
            "El equipo consolidó el backlog de iniciativas con impacto en 90 días.",
            "Se mantiene la cadencia de seguimiento semanal con el comité digital.",
        ),
    ),
    "P2026-021": ContentPack(
        slug="P2026-021",
        display_name="P2026-021 Due diligence",
        sector="due diligence",
        lexicon=(
            "hallazgos documentales", "riesgo residual", "carpeta de evidencias",
            "contratos materiales", "contigencias",
        ),
        metrics=("hallazgos altos 2", "medios 7", "cobertura documental 86%"),
        topics=("revisión legal-financiera", "matriz de hallazgos", "cierre de observaciones"),
        products=("Estado semanal", "Kickoff notes", "Registro de riesgos"),
        filler_paragraphs=(
            "La carpeta de evidencias se actualiza tras cada ronda de preguntas.",
            "Los hallazgos altos requieren plan de mitigación antes del cierre.",
        ),
    ),
    "P2026-033": ContentPack(
        slug="P2026-033",
        display_name="P2026-033 Optimización de cadena",
        sector="cadena de suministro",
        lexicon=(
            "lead time", "inventario de seguridad", "OTIF", "proveedor crítico",
            "plan de reabastecimiento",
        ),
        metrics=("lead time -1.5 días", "stockout -12%", "costo logístico -4%"),
        topics=("tablero OTIF", "negociaciones de lead time", "rediseño de buffer"),
        products=("Estado semanal", "Anexo de stakeholders", "Registro de riesgos"),
        filler_paragraphs=(
            "Se modelaron escenarios de buffer para SKUs de alta rotación.",
            "El comité logístico aprobó el piloto en el centro de distribución Lima.",
        ),
    ),
}

_CASOS = ContentPack(
    slug="casos",
    display_name="Fixtures de laboratorio",
    sector="casos de estudio DAP Laya",
    lexicon=("fixture", "ground truth", "clasificación", "sanitización"),
    metrics=("casos 01–05", "etiquetas limpio/con_pii"),
    topics=("informe sensible", "CSV de clientes", "proyecto mixto", "semilla corrupta"),
    products=("CASO 01", "CASO 02", "CASO 04", "CASO 05"),
    filler_paragraphs=(
        "Documento de control para los casos de estudio del laboratorio.",
        "El contenido es sintético y no corresponde a operaciones reales.",
    ),
)


def content_pack_for(path: str) -> ContentPack:
    lower = path.replace("\\", "/").lower()
    for key, pack in _CLIENTS.items():
        if key in lower:
            return pack
    for code, pack in _PROJECTS.items():
        if code.lower() in lower:
            return pack
    if lower.startswith("casos/") or "/casos/" in lower:
        return _CASOS
    if "interno/rrhh" in lower:
        return _RRHH
    if "interno/finanzas" in lower:
        return _FINANZAS
    if "interno/legal" in lower:
        return _LEGAL
    if "interno/ops" in lower:
        return _OPS
    if lower.startswith("publico/") or "/publico/" in lower:
        return _PUBLICO
    return _PUBLICO
