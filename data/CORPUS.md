# Corpus sintético — Andes Advisory S.A.C.

Diseño del repositorio de archivos del laboratorio **DAP Laya**. Los datos son **ficticios**; no representan clientes, colaboradores ni cuentas reales. Este documento es la especificación de diseño; el inventario máquina-legible está en `manifest.json`.

## 1. Persona de la firma

| Campo | Valor |
|-------|--------|
| Razón social | Andes Advisory S.A.C. |
| Rubro | Consultoría en estrategia y transformación digital |
| Sede | Lima, Perú |
| Idioma documental | Español (PE) |
| Identificadores | DNI (8 dígitos), RUC (11 dígitos) |
| Teléfonos | `+51 …`, `01-…`, `9xx xxx xxx` |
| Moneda en reportes | PEN / USD |

**Cuentas de cliente ficticias:** Banco Andino, Retail Pacífico, Minera Sierra, Clínica Salud Lima, Agro Valle.

## 2. Rol en el laboratorio

El árbol bajo `data/files/` se monta en el host protegido como `/files` (volumen compartido Flask + DLP). Sirve para:

1. Ejercitar la ACL en cascada `(usuario, ruta) → sensibilidad`.
2. Proveer etiquetas de referencia (`limpio` / `con_pii`) frente a las cuales se evalúa Laya.
3. Alimentar los cinco casos de estudio del README (§11).

La evaluación de clasificación usa este ground truth; Laya **no** es el oráculo.

## 3. Árbol de directorios

```text
files/
  publico/                 # marketing, catálogos, boletines (limpios; trampas FP)
  interno/
    rrhh/                  # alta densidad de PII de colaboradores
    finanzas/              # facturas, CCI, contactos de cobranzas
    legal/                 # extractos de contrato / NDA
    ops/                   # procedimientos (limpios)
  clientes/
    banco_andino/{entregables,confidencial}/
    retail_pacifico/{entregables,confidencial}/
    minera_sierra/{entregables,confidencial}/
    clinica_salud_lima/{entregables,confidencial}/
    agro_valle/{entregables,confidencial}/
  proyectos/
    P2026-014_transformacion_digital/
    P2026-021_due_diligence/
    P2026-033_optimizacion_cadena/
  casos/                   # fixtures explícitos CASO 01, 02, 04
```

La anidación permite políticas ACL del tipo `/files/clientes/` → `media` frente a `/files/clientes/banco_andino/confidencial/` → solo `alta`. Ver `acl_paths.example.yaml`.

## 4. Cupos objetivo

| Área | Archivos | Con PII | Notas |
|------|----------|---------|--------|
| `publico/` | 35 | 0 | Trampas de falso positivo (CASO 05) |
| `interno/rrhh/` | 8 | 5 | |
| `interno/finanzas/` | 8 | 3 | |
| `interno/legal/` | 6 | 2 | |
| `interno/ops/` | 8 | 0 | |
| `clientes/*` | 20 | 5 | |
| `proyectos/*` | 12 | 2 | |
| `casos/` | 4 | 3 | + 1 ilegible de control |
| **Total** | **≈ 101** | **≈ 20** | ≈ 81 limpios |

Tolerancia: ±5 archivos; la fuente de verdad de conteos es `manifest.json`.

## 5. Formatos

| Formato | Uso |
|---------|-----|
| `.txt` | Ground truth con offsets de carácter exactos |
| `.csv` | Listas tabulares (CASO 02); offsets sobre el texto CSV canónico |
| `.pdf` | Realismo de entregable; spans sobre **texto extraído** |
| `.docx` | Idem Word |
| `.bin` / PDF truncado | 1–2 semillas ilegibles: se registran aparte, **no** como PII |

## 6. Catálogo de tipos PII (ground truth)

| Tipo | Ejemplo sintético |
|------|-------------------|
| `given_name` | Lucía |
| `surname` | Quispe |
| `email_address` | lucia.quispe@bancoandino.pe |
| `phone_number` | +51 989 123 456 |
| `id_card_number` | 45678912 (DNI) |
| `street` | Av. Larco 123 |
| `city` | Miraflores |
| `postal_code` | 15074 |
| `bank_account` | CCI 002-1-123456789012 |
| `credit_card_number` | uso escaso (1–2 archivos) |
| `organization_tax_id` | RUC 20123456789 |

Los tipos siguen la nomenclatura cercana a Laya Experts · PII; `organization_tax_id` es etiqueta local (Stage 1 por reglas; Laya puede no confirmarla).

### 6.1 Distractores (no PII)

Deben permanecer con `label: limpio`:

- SKU / código de producto de 8 dígitos (misma longitud que un DNI)
- Códigos de proyecto (`P2026-014`)
- Hotlines corporativas (`01-615-8000`)
- Léxico: «proyección», «confidencialidad», «DNI» sin número adyacente

## 7. Plantillas de generación

| ID de plantilla | Clase | Etiqueta típica |
|-----------------|-------|-----------------|
| `boletin_catalogo` | Boletín / catálogo | limpio + `fp_traps` |
| `client_contact_list` | CSV de contactos / clientes | con_pii |
| `informe_proyecto` | Informe narrativo + contactos | mixto |
| `contrato_extracto` | Contrato / NDA | con_pii |
| `nota_rrhh` | Nota o ficha RRHH | con_pii |
| `factura_liquidacion` | Factura / liquidación | con_pii (ligera) |
| `procedimiento_ops` | Procedimiento interno | limpio |
| `corrupt_seed` | Archivo ilegible | limpio (error de lectura) |

## 8. Esquema del manifiesto

`manifest.json` es un arreglo de registros:

| Campo | Significado |
|-------|-------------|
| `id` | Identificador estable (`pub-001`, `rrhh-003`, …) |
| `path` | Ruta relativa a `files/` |
| `format` | `txt` \| `csv` \| `pdf` \| `docx` \| `bin` |
| `label` | `limpio` \| `con_pii` |
| `template` | ID de plantilla (§7) |
| `case_tags` | Subconjunto de `caso01`…`caso05`, `caso03` |
| `acl_hint_path` | Prefijo ACL sugerido (`/files/...`) |
| `expected_spans` | Lista `{type, text, start?, end?}`; vacía si limpio |
| `fp_traps` | Lista de distractores presentes en el archivo |
| `notes` | Texto libre |

Reglas:

- `expected_spans` vacío ⇔ `label == limpio` (salvo semillas corruptas, también limpio sin spans).
- Offsets (`start`/`end`) aplican al **texto canónico** del generador para `txt`/`csv`. En `pdf`/`docx` los spans listan `text` (+ `type`); los offsets se materializan tras extracción.
- El manifiesto se define **antes** de emitir binarios; el generador es determinista con `--seed`.

## 9. Mapa a casos de estudio

| Caso | Uso del corpus |
|------|----------------|
| 01 | `casos/caso01_informe_sensible.*` — PII; solicitante con sensibilidad `baja` en esa ruta → **denegado** |
| 02 | `casos/caso02_clientes_demo.csv` — columnas del Informe; `media` → **sanitizado** |
| 03 | Árbol completo (~100); latencia caché fría vs. caliente; invalidación por hash |
| 04 | `casos/caso04_proyecto_mixto.*` — mismo archivo bajo `alta` / `media` / `baja` |
| 05 | Todos los `label=limpio` (~80), en especial `publico/` con `fp_traps` → siempre **completo** |

## 10. Generación

Implementación: paquete `src/corpus_gen/` con entrypoints `scripts/generate_corpus.py`, `.ps1` y `.sh` (usan `.venv`).

```bash
pip install -r requirements.txt
.\scripts\generate_corpus.ps1 --dry-run
.\scripts\generate_corpus.ps1 --seed 20261114
# Opcional: párrafos asistidos por Ollama (caché en data/corpus_bodies/)
.\scripts\generate_corpus.ps1 --seed 20261114 --llm
.\scripts\generate_corpus.ps1 --llm --refresh-llm --ollama-model mistral-nemo:latest
```

1. Leer `manifest.json`.
2. Elegir variante de plantilla + content pack según ruta (cliente/área/proyecto).
3. (Opcional `--llm`) Pedir a Ollama 3–5 párrafos sin PII; cachear por `seed`/`file_id`/modelo.
4. Ensamblar texto canónico: narrativa + PII embebida (ficha / firma / correo / prosa) + trampas FP.
5. Escribir bajo `data/files/<path>` (`txt`/`csv`/`pdf`/`docx`/`bin`).
6. Recalcular offsets sobre el texto canónico y reescribir `expected_spans` en el manifiesto.
7. Validar: trampas FP en `txt`/`csv` limpios; semilla corrupta sin spans PII.

Semilla por defecto: `20261114`. Dependencias: `python-docx`, `fpdf2`. Ollama es opcional (`mistral-nemo:latest` por defecto; `CORPUS_OLLAMA_MODEL` / `CORPUS_OLLAMA_HOST`). El inventario de rutas se regenera con `scripts/_build_manifest.py` si hace falta.

## 11. Límites

El corpus emula un filesystem de consultora a escala de laboratorio. No afirma cobertura estadística de PII peruano real ni equivalencia con un data lake empresarial.
