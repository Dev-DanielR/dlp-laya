"""Deterministic PE-flavoured synthetic value pools."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


GIVEN_NAMES = [
    "Lucía", "María", "Ana", "Carmen", "Rosa", "Elena", "Patricia", "Claudia",
    "Diego", "Carlos", "José", "Luis", "Miguel", "Andrés", "Fernando", "Jorge",
    "Sofía", "Valeria", "Camila", "Daniela", "Sebastián", "Ricardo", "Pedro",
    "Alejandra", "Gabriela", "Renato", "Bruno", "Inés", "Pilar", "Óscar",
    "Natalia", "Fabiola", "Héctor", "Iván", "Jimena", "Karina", "Leonardo",
    "Mónica", "Noelia", "Omar", "Paola", "Rocío", "Sergio", "Tatiana",
    "Úrsula", "Víctor", "Wendy", "Xavier", "Yolanda", "Zulema", "Álvaro",
]

SURNAMES = [
    "Quispe", "Huamán", "García", "Rodríguez", "Flores", "Rojas", "Vargas",
    "Castillo", "Mendoza", "Torres", "Chávez", "Ramírez", "Salazar", "Paredes",
    "Cárdenas", "Espinoza", "Navarro", "Silva", "Cruz", "Reyes", "Morales",
    "Delgado", "Aguilar", "Castro", "Romero", "Vega", "Ríos", "León",
    "Alarcón", "Bustamante", "Córdova", "Díaz", "Esteban", "Fuentes",
    "Guzmán", "Herrera", "Ibáñez", "Jáuregui", "Lozano", "Meza", "Núñez",
    "Ortega", "Pacheco", "Quiroz", "Ruiz", "Sánchez", "Tapia", "Ugarte",
]

CITIES = [
    "Miraflores", "San Isidro", "Surco", "La Molina", "Jesús María",
    "San Borja", "Barranco", "Pueblo Libre", "Lince", "Magdalena",
    "Arequipa", "Cusco", "Trujillo", "Piura", "Huancayo",
    "Chiclayo", "Iquitos", "Tacna", "Cajamarca", "Puno",
]

STREETS = [
    "Av. Larco", "Av. Javier Prado", "Av. Arequipa", "Calle Los Pinos",
    "Jr. de la Unión", "Av. Brasil", "Calle Las Begonias", "Av. El Sol",
    "Jr. Cusco", "Av. Salaverry", "Calle Schell", "Av. Benavides",
    "Av. República de Panamá", "Calle Las Orquídeas", "Jr. Lampa",
    "Av. Angamos Este", "Calle Los Cedros", "Av. Primavera",
]

JOB_TITLES = [
    "Analista de datos", "Consultor senior", "Gerente de proyecto",
    "Especialista en ciberseguridad", "Líder técnico", "Coordinador de PMO",
    "Arquitecto de soluciones", "Analista de calidad", "Asesor legal",
    "Ejecutivo de cuenta", "Controller financiero", "Ingeniero de procesos",
]

AREAS = [
    "Consultoría", "Operaciones", "Finanzas", "Legal", "RRHH",
    "Ciberseguridad", "Datos", "PMO", "Comercial", "Soporte",
]

INVOICE_CONCEPTS = [
    "Servicios de consultoría estratégica",
    "Diagnóstico de madurez digital",
    "Implementación de controles de acceso",
    "Acompañamiento PMO Q1",
    "Auditoría de procesos de datos",
    "Capacitación in-company (16 h)",
    "Due diligence documental",
    "Optimización de cadena de suministro",
]

RISK_IDS = [
    "R-01 Continuidad", "R-02 Cumplimiento", "R-03 Integración",
    "R-04 Disponibilidad", "R-05 Terceros", "R-06 Cambio organizacional",
    "R-07 Calidad de datos", "R-08 Seguridad de la información",
]

EMAIL_DOMAINS = [
    "bancoandino.pe", "retailpacifico.pe", "minerasierra.pe",
    "clinicasaludlima.pe", "agrovalle.pe", "andesadvisory.pe",
    "correo.pe", "empresa.pe",
]

ORGS = [
    "Banco Andino", "Retail Pacífico", "Minera Sierra",
    "Clínica Salud Lima", "Agro Valle", "Andes Advisory S.A.C.",
]

HOTLINE = "01-615-8000"
PROJECT_CODES = ["P2026-014", "P2026-021", "P2026-033", "P2026-041", "P2026-055"]


def file_rng(seed: int, file_id: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{file_id}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _luhn_complete(prefix: str) -> str:
    digits = [int(c) for c in prefix]
    checksum_sum = 0
    parity = (len(digits) + 1) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum_sum += d
    check = (10 - (checksum_sum % 10)) % 10
    return prefix + str(check)


@dataclass(frozen=True)
class Person:
    given_name: str
    surname: str
    id_card_number: str
    email_address: str
    phone_number: str
    street: str
    city: str
    postal_code: str
    bank_account: str
    credit_card_number: str
    organization_tax_id: str

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.surname}"


def make_dni(rng: random.Random) -> str:
    return f"{rng.randint(10_000_000, 79_999_999)}"


def make_ruc(rng: random.Random) -> str:
    return f"20{rng.randint(100_000_000, 999_999_999)}"


def make_phone(rng: random.Random) -> str:
    return f"+51 9{rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"


def make_cci(rng: random.Random) -> str:
    return f"002-1-{rng.randint(100000000000, 999999999999)}"


def make_card(rng: random.Random) -> str:
    # Synthetic Visa-like 16-digit with Luhn; not a real BIN.
    prefix = "4111" + "".join(str(rng.randint(0, 9)) for _ in range(11))
    return _luhn_complete(prefix)


def make_sku(rng: random.Random) -> str:
    return f"{rng.randint(10_000_000, 99_999_999)}"


def make_postal(rng: random.Random) -> str:
    return f"{rng.randint(15001, 15999)}"


def _slug(text: str) -> str:
    out = text.lower()
    for a, b in (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ñ", "n"), ("ü", "u"),
    ):
        out = out.replace(a, b)
    return out


def make_person(rng: random.Random, *, domain: str | None = None) -> Person:
    given = rng.choice(GIVEN_NAMES)
    surname = rng.choice(SURNAMES)
    local = f"{_slug(given)}.{_slug(surname)}"
    dom = domain or rng.choice(EMAIL_DOMAINS)
    street_n = rng.randint(100, 1999)
    return Person(
        given_name=given,
        surname=surname,
        id_card_number=make_dni(rng),
        email_address=f"{local}@{dom}",
        phone_number=make_phone(rng),
        street=f"{rng.choice(STREETS)} {street_n}",
        city=rng.choice(CITIES),
        postal_code=make_postal(rng),
        bank_account=make_cci(rng),
        credit_card_number=make_card(rng),
        organization_tax_id=make_ruc(rng),
    )


def value_for_type(person: Person, span_type: str, rng: random.Random) -> str:
    mapping = {
        "given_name": person.given_name,
        "surname": person.surname,
        "email_address": person.email_address,
        "phone_number": person.phone_number,
        "id_card_number": person.id_card_number,
        "street": person.street,
        "city": person.city,
        "postal_code": person.postal_code,
        "bank_account": person.bank_account,
        "credit_card_number": person.credit_card_number,
        "organization_tax_id": person.organization_tax_id,
    }
    if span_type not in mapping:
        raise ValueError(f"unknown span type: {span_type}")
    return mapping[span_type]
