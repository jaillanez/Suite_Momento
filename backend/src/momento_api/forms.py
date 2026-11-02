"""Antecedentes y datos de ingreso de la persona, según la planilla del equipo.

Fuente: "Escalas Momento Instituciones" (hojas de antecedentes). Las preguntas y
opciones se transcriben tal cual; el sistema solo valida y calcula el IMC.
"""

from __future__ import annotations

from typing import Any

NO = ("no", "No")
YES = ("si", "Sí")
NO_YES = [NO, YES]
NO_YES_BEFORE = [NO, YES, ("antes", "Antes sí, pero ahora no")]


def choice(key: str, label: str, options: list[tuple[str, str]], *, detail_for: tuple[str, ...] = (),
           detail_label: str = "Especificar", number_for: tuple[str, ...] = (), number_label: str = "",
           number_min: float = 0, number_max: float = 100) -> dict[str, Any]:
    field: dict[str, Any] = {"key": key, "label": label, "type": "choice",
                             "options": [{"value": v, "label": t} for v, t in options]}
    if detail_for:
        field["detail"] = {"for": list(detail_for), "label": detail_label}
    if number_for:
        field["number"] = {"for": list(number_for), "label": number_label, "min": number_min, "max": number_max}
    return field


def multi(key: str, label: str, options: list[tuple[str, str]], *, detail_label: str | None = None) -> dict[str, Any]:
    field: dict[str, Any] = {"key": key, "label": label, "type": "multi",
                             "options": [{"value": v, "label": t} for v, t in options]}
    if detail_label:
        field["detail"] = {"for": ["*"], "label": detail_label}
    return field


def number(key: str, label: str, minimum: float, maximum: float, unit: str = "", step: float = 1) -> dict[str, Any]:
    return {"key": key, "label": label, "type": "number", "min": minimum, "max": maximum, "unit": unit, "step": step}


def text(key: str, label: str) -> dict[str, Any]:
    return {"key": key, "label": label, "type": "text"}


BACKGROUND_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "senses",
        "title": "Sentidos y movilidad",
        "fields": [
            choice("vision", "¿Tiene alguna alteración visual? ¿Usa algún correctivo?",
                   [NO, ("si_sin", "Sí, no usa ningún correctivo"), ("anteojos", "Sí, usa anteojos")]),
            choice("hearing", "¿Tiene alguna alteración auditiva? ¿Usa algún correctivo?",
                   [NO, ("si_sin", "Sí, no usa ningún correctivo"), ("audifonos", "Sí, usa audífonos"),
                    ("otro", "Sí, usa otro tipo de correctivo")]),
            choice("gait", "¿Tiene alguna dificultad para caminar o alteración en la marcha?", NO_YES),
            choice("walking_aid", "¿Usa algún soporte o ayuda para caminar?",
                   [NO, ("baston", "Sí, bastón"), ("muletas", "Sí, muletas"), ("andador", "Sí, andador"),
                    ("silla", "Sí, silla de ruedas"), ("otro", "Sí, otro")], detail_for=("otro",)),
            multi("physical_activity", "¿Realizaba alguna actividad física previa al ingreso? (puede ser más de una)",
                  [("gimnasia", "Gimnasia (con profesor)"), ("caminata", "Caminata"), ("bicicleta", "Bicicleta"),
                   ("deporte", "Deporte en equipo"), ("danzas", "Danzas"), ("otros", "Otros")],
                  detail_label="Detalle"),
        ],
    },
    {
        "id": "habits",
        "title": "Sueño y hábitos",
        "fields": [
            number("sleep_hours", "¿Cuántas horas duerme por día?", 0, 24, "horas", 0.5),
            choice("sleep_onset", "¿Tiene dificultad para conciliar el sueño?", NO_YES),
            choice("sleep_maintenance", "¿Tiene dificultad para mantener el sueño? (despertares)", NO_YES),
            choice("smoking", "¿Fuma?", [NO, ("antes", "Antes sí, ahora no"), YES],
                   number_for=("si",), number_label="Cigarrillos por día", number_max=100),
            choice("alcohol", "¿Toma alcohol? (vino, cerveza, bebidas blancas)",
                   [NO, ("diario", "Sí, todos los días"), ("varias_semana", "Sí, más de una vez por semana"),
                    ("semanal", "Sí, una vez por semana"), ("mensual", "Sí, una vez al mes"),
                    ("ocasional", "Sí, ocasional")]),
            choice("drugs", "¿Consume drogas?", NO_YES, detail_for=("si",)),
        ],
    },
    {
        "id": "personal",
        "title": "Antecedentes personales",
        "fields": [
            choice("childhood", "Antecedentes médicos en la infancia", NO_YES, detail_for=("si",)),
            choice("dizziness", "¿Sufre de mareos?", NO_YES_BEFORE),
            choice("vertigo", "¿Sufre de vértigo?", NO_YES_BEFORE),
            choice("tremor", "¿Sufre de temblores?", NO_YES_BEFORE),
            choice("headache", "¿Sufre de dolores de cabeza (cefaleas)?", NO_YES_BEFORE),
            choice("dx_clinical", "¿Presenta algún diagnóstico clínico?", NO_YES, detail_for=("si",),
                   detail_label="Cuál (HTA, diabetes, colesterol, oncológico, cardiológico, trasplante, renal, respiratorio, tiroides…)"),
            choice("dx_neuro", "¿Presenta algún diagnóstico neurológico?", NO_YES, detail_for=("si",),
                   detail_label="Cuál (demencia tipo Alzheimer, Parkinson, ACV, TEC…)"),
            choice("dx_psych", "¿Presenta algún diagnóstico psiquiátrico?", NO_YES, detail_for=("si",),
                   detail_label="Cuál (depresión, trastorno bipolar, esquizofrenia…)"),
            number("covid_times", "¿Ha padecido COVID? ¿Cuántas veces? (0 = no)", 0, 20),
            number("covid_doses", "¿Recibió la vacuna contra el COVID? ¿Cuántas dosis? (0 = no)", 0, 20),
            multi("surgery", "Antecedentes quirúrgicos (dejar vacío si no tiene)",
                  [("neuro", "Neurocirugía"), ("cardio", "Cardiológica"), ("trauma", "Traumatológica"),
                   ("otra", "Otra")], detail_label="Detalle"),
            text("other_history", "Otro antecedente clínico personal de relevancia"),
        ],
    },
    {
        "id": "cognition",
        "title": "Estado cognitivo y funcional",
        "fields": [
            choice("cognitive_impairment", "Deterioro cognitivo",
                   [("no", "No hay deterioro"), ("leve", "Sí, grado leve"), ("moderado", "Sí, grado moderado"),
                    ("severo", "Sí, grado severo")]),
            multi("affected_domains", "¿Qué dominios tiene afectados? (puede ser más de uno)",
                  [("orientacion", "Orientación"), ("atencion", "Atención"), ("memoria", "Memoria"),
                   ("lenguaje", "Lenguaje"), ("ejecutivas", "Funciones ejecutivas"),
                   ("visopercepcion", "Visopercepción"), ("praxias", "Praxias"), ("social", "Cognición social")]),
            choice("daily_living", "Afectación de actividades de la vida cotidiana", NO_YES, detail_for=("si",),
                   detail_label="En qué requiere asistencia"),
        ],
    },
    {
        "id": "admission",
        "title": "Datos de ingreso",
        "fields": [
            number("weight", "Peso", 20, 250, "kg", 0.1),
            number("height", "Talla", 1.0, 2.3, "m", 0.01),
            number("systolic", "Tensión arterial sistólica", 30, 300, "mmHg"),
            number("diastolic", "Tensión arterial diastólica", 30, 300, "mmHg"),
            number("heart_rate", "Ritmo cardíaco", 30, 300, "lpm"),
            text("admission_medication", "Plan farmacológico al ingreso (droga y dosis)"),
            text("adverse_reactions", "Comentarios sobre reacciones adversas a fármacos"),
            text("studies_summary", "Resumen de estudios complementarios (resonancia, etc.)"),
        ],
    },
    {
        "id": "family",
        "title": "Antecedentes familiares",
        "fields": [
            choice("family_clinical", "Enfermedades clínicas", NO_YES, detail_for=("si",), detail_label="Cuál y quién"),
            choice("family_neuro", "Enfermedades neurológicas", NO_YES, detail_for=("si",), detail_label="Cuál y quién"),
            choice("family_psych", "Enfermedades psiquiátricas", NO_YES, detail_for=("si",), detail_label="Cuál y quién"),
        ],
    },
    {
        "id": "autonomy",
        "title": "Autonomía y tecnología",
        "fields": [
            multi("independent_activities", "¿Qué actividades puede realizar con independencia y autonomía?",
                  [("mate", "Preparar té o mate"), ("receta", "Preparar una receta sencilla"),
                   ("ropa", "Lavado de ropa"), ("jardin", "Cuidado de jardín"), ("costura", "Costura")]),
            multi("technology", "¿Utiliza tecnología? (dejar vacío si no)",
                  [("celular", "Celular"), ("tablet", "Tablet"), ("computadora", "Computadora")]),
        ],
    },
]

_FIELDS = {field["key"]: field for section in BACKGROUND_SECTIONS for field in section["fields"]}


def body_mass_index(answers: dict[str, Any]) -> float | None:
    """IMC = peso / talla²; se calcula, no se carga."""
    weight, height = answers.get("weight"), answers.get("height")
    if isinstance(weight, (int, float)) and isinstance(height, (int, float)) and height > 0:
        return round(weight / (height * height), 1)
    return None


def clean_background(raw: dict[str, Any]) -> dict[str, Any]:
    """Valida respuestas contra la definición y descarta lo vacío.

    Lanza ValueError con un mensaje en español si algo no corresponde.
    """
    clean: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "bmi":  # calculado por el sistema; se ignora si vuelve del cliente
            continue
        base, _, suffix = key.partition("__")
        field = _FIELDS.get(base)
        if field is None or suffix not in ("", "detail", "number"):
            raise ValueError("Hay un dato de antecedentes que no corresponde a la planilla.")
        if value is None or value == "" or value == []:
            continue
        if suffix == "detail":
            if "detail" not in field or not isinstance(value, str):
                raise ValueError(f"«{field['label']}» no admite detalle.")
            clean[key] = value.strip()[:2000]
        elif suffix == "number":
            spec = field.get("number")
            if not spec or not isinstance(value, (int, float)) or not spec["min"] <= value <= spec["max"]:
                raise ValueError(f"Revisá el número de «{field['label']}».")
            clean[key] = value
        elif field["type"] == "choice":
            if not isinstance(value, str) or value not in {option["value"] for option in field["options"]}:
                raise ValueError(f"Opción inválida en «{field['label']}».")
            clean[key] = value
        elif field["type"] == "multi":
            allowed = {option["value"] for option in field["options"]}
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value) or not set(value) <= allowed:
                raise ValueError(f"Opción inválida en «{field['label']}».")
            clean[key] = [option["value"] for option in field["options"] if option["value"] in value]
        elif field["type"] == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not field["min"] <= value <= field["max"]:
                raise ValueError(f"«{field['label']}» debe estar entre {field['min']} y {field['max']}.")
            clean[key] = value
        else:
            if not isinstance(value, str):
                raise ValueError(f"«{field['label']}» debe ser texto.")
            clean[key] = value.strip()[:4000]

    # El detalle o número solo se guardan si la opción elegida los habilita.
    for key in list(clean):
        base, _, suffix = key.partition("__")
        if suffix:
            field = _FIELDS[base]
            spec = field.get(suffix)
            selected = clean.get(base)
            enabled = (
                spec is not None
                and selected not in (None, [])
                and ("*" in spec["for"] or selected in spec["for"])
            )
            if not enabled:
                del clean[key]
    if (bmi := body_mass_index(clean)) is not None:
        clean["bmi"] = bmi
    return clean
