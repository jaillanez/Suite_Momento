"""Escalas de evaluación y su puntaje.

Fuente: planilla "Escalas Momento Instituciones" y apuntes de revisión de Jorge
(03/09/2026). El sistema suma puntos según la planilla; no interpreta resultados
salvo los rangos que la planilla define (Barthel). Los puntos que se apartan de la
planilla están marcados con «CORRECCIÓN» y documentados en docs/escalas.md. Los valores
que el equipo puede ajustar (Barthel, restas, tablas de fluencia) están en scale_parameters.py.
"""

from __future__ import annotations

from typing import Any

from momento_api.scale_parameters import (
    BARTHEL_BANDS,
    BARTHEL_EATING,
    FLUENCY_ANIMALS_TABLE,
    FLUENCY_LETTERS_TABLE,
    SERIAL7_RELATIVE_TO_PREVIOUS,
)

# --- Constructores de ítems --------------------------------------------------


def choice(key: str, label: str, options: list[tuple[str, int]], domain: str | None = None) -> dict[str, Any]:
    return {
        "key": key, "label": label, "type": "choice", "domain": domain,
        "options": [{"value": str(index), "label": text, "points": points} for index, (text, points) in enumerate(options)],
    }


def checks(key: str, label: str, items: list[str], domain: str | None, scoring: str = "count",
           instruction: str = "", max_points: int | None = None) -> dict[str, Any]:
    if max_points is None:
        max_points = {"count": len(items), "all": 1, "repeat_words": 2, "writing": 2, "none": 0}[scoring]
    return {"key": key, "label": label, "type": "checks", "domain": domain, "items": items,
            "scoring": scoring, "instruction": instruction, "max": max_points}


# --- Barthel -----------------------------------------------------------------

BARTHEL = {
    "code": "barthel",
    "name": "Índice de Barthel",
    "description": "Actividades básicas de la vida diaria.",
    "sections": [{"title": "Actividades", "items": [
        # CORRECCIÓN: la planilla da 15 a "Comer – Independiente" (total 105). Valor en scale_parameters.py.
        choice("comer", "Comer", BARTHEL_EATING),
        choice("traslado", "Trasladarse entre la silla y la cama", [
            ("Incapaz, no se mantiene sentado", 0), ("Necesita ayuda importante, puede estar sentado", 5),
            ("Necesita algo de ayuda", 10), ("Independiente", 15)]),
        choice("aseo", "Aseo personal", [("Necesita ayuda", 0), ("Independiente para lavarse la cara, las manos y peinarse", 5)]),
        choice("retrete", "Uso del retrete", [("Dependiente", 0), ("Necesita alguna ayuda", 5), ("Independiente", 10)]),
        choice("bano", "Bañarse o ducharse", [("Dependiente", 0), ("Independiente", 5)]),
        choice("desplazarse", "Desplazarse", [
            ("Inmóvil", 0), ("Independiente en silla de ruedas 50 m", 5), ("Anda con pequeña ayuda de una persona", 10),
            ("Independiente al menos 50 m con cualquier tipo de muleta, excepto andador", 15)]),
        choice("escaleras", "Subir y bajar escaleras", [("Incapaz", 0), ("Necesita ayuda física o verbal", 5), ("Independiente", 10)]),
        choice("vestirse", "Vestirse y desvestirse", [("Dependiente", 0), ("Necesita ayuda pero puede la mitad sin ayuda", 5), ("Independiente", 10)]),
        choice("heces", "Control de heces", [("Incontinente", 0), ("Accidente excepcional (uno por semana)", 5), ("Continente", 10)]),
        choice("orina", "Control de orina", [
            ("Incontinente o sondado incapaz de cambiarse la bolsa", 0), ("Accidente excepcional (uno cada 24 h)", 5),
            ("Continente durante al menos 7 días", 10)]),
    ]}],
}

# Los rangos de interpretación (BARTHEL_BANDS) están en scale_parameters.py.

# --- Yesavage (GDS-15) -------------------------------------------------------

_GDS = [
    ("En general, ¿está satisfecho/a con su vida?", 0),
    ("¿Ha abandonado muchas de sus tareas habituales y aficiones?", 1),
    ("¿Siente que su vida está vacía?", 1),
    ("¿Se siente con frecuencia aburrido/a?", 1),
    ("¿Se encuentra de buen humor la mayor parte del tiempo?", 0),
    ("¿Teme que algo malo pueda ocurrirle?", 1),
    ("¿Se siente feliz la mayor parte del tiempo?", 0),
    ("¿Con frecuencia se siente desamparado/a, desprotegido/a, abandonado/a?", 1),
    ("¿Prefiere quedarse en casa, más que salir y hacer cosas nuevas?", 1),
    ("¿Cree que tiene más problemas de memoria que la mayoría de la gente?", 1),
    ("En estos momentos, ¿piensa que es estupendo estar vivo/a?", 0),
    ("¿Actualmente se siente un/a inútil?", 1),
    ("¿Se siente lleno/a de energía?", 0),
    ("¿Siente que su situación actual es desesperada?", 1),
    ("¿Piensa que la mayoría de la gente está en mejor situación que usted?", 1),
]

GDS15 = {
    "code": "gds15",
    "name": "Escala de depresión geriátrica de Yesavage (GDS-15)",
    "description": "15 preguntas de respuesta Sí/No.",
    "sections": [{"title": "Preguntas", "items": [
        choice(f"p{index}", text, [("Sí", yes_points), ("No", 1 - yes_points)])
        for index, (text, yes_points) in enumerate(_GDS, start=1)
    ]}],
}

# --- Cuestionario de quejas cognitivas (CQC) ---------------------------------

_FREQUENCY = [("Nunca", 0), ("Casi nunca", 1), ("A veces", 2), ("Con frecuencia", 3), ("Siempre", 4)]
_CQC = {
    "Atención": [
        "Se distrae con facilidad, por ejemplo cuando lee, mira una película o conversa con alguien.",
        "Necesita prestar más atención que antes o hacer más esfuerzos que otros para realizar las tareas.",
        "Pierde el hilo del pensamiento, por ejemplo cuando está conversando con alguien cambia de tema en tema.",
        "Le resulta difícil hacer más de una cosa a la vez.",
    ],
    "Orientación": [
        "Tiene problemas para orientarse en lugares conocidos (por ejemplo, su barrio).",
        "Tiene problemas para encontrar alguna habitación dentro de su propia casa o institución que frecuenta (por ejemplo, baño).",
        "Se equivoca o no está seguro de la fecha (día, mes y año).",
        "Tiene dificultades para decir con precisión su edad actual.",
    ],
    "Funciones ejecutivas": [
        "Le cuesta tomar decisiones o decidir qué hacer.",
        "Tiene dificultades para organizar planes, por ejemplo una salida con amigos.",
        "Presenta dificultades para hacer cambios de planes o cambiar la actividad cuando es necesario.",
        "Dificultad para seguir el orden de pasos necesario para realizar una tarea (por ejemplo, cocinar, vestirse) o deja cosas sin terminar.",
    ],
    "Memoria": [
        "Olvida o confunde los nombres de personas conocidas (por ejemplo, nombres de nietos o amigos).",
        "Olvida citas o planes previamente pautados.",
        "Olvida el lugar donde dejó objetos de uso cotidiano (por ejemplo, llaves, anteojos, celular).",
        "Algunas veces no recuerda hechos recientes (por ejemplo, qué almorzó ayer, quién llamó por teléfono).",
    ],
    "Praxias y gnosias": [
        "Tiene dificultades para vestirse (no por problemas motrices, por ejemplo, prender los botones de la camisa).",
        "Le cuesta hacer o copiar dibujos.",
        "Tiene dificultades para reconocer objetos o personas que conoce.",
        "Le cuesta encontrar objetos, particularmente cuando no están en la posición habitual.",
    ],
    "Lenguaje": [
        "Tiene dificultades para encontrar la palabra correcta.",
        "Le cuesta escribir, su letra empeoró en el último tiempo.",
        "Le resulta difícil entender lo que otros dicen.",
        "Le cuesta entender lo que lee.",
    ],
}

CQC = {
    "code": "cqc",
    "name": "Cuestionario de quejas cognitivas (CQC)",
    "description": "24 preguntas de frecuencia: Nunca (0) a Siempre (4). Máximo 16 por dominio y 96 en total.",
    "sections": [
        {"title": domain, "items": [choice(f"{index}_{n}", text, _FREQUENCY, domain=domain) for n, text in enumerate(texts)]}
        for index, (domain, texts) in enumerate(_CQC.items())
    ],
}

# --- ACE-III -----------------------------------------------------------------

ADDRESS = ["Luis", "Reynal", "Pedro", "Goyena", "420", "Rosario", "Santa Fe"]
RECOGNITION = [
    # (clave, etiqueta, opciones, correcta, ítems del recuerdo que la acreditan)
    ("nombre", "Nombre", ["Lucas Reynal", "Luis Reynal", "Luis Royal"], "Luis Reynal", ["Luis", "Reynal"]),
    ("calle", "Calle", ["Pedro Galeano", "Pablo Goyena", "Pedro Goyena"], "Pedro Goyena", ["Pedro", "Goyena"]),
    ("numero", "Número", ["240", "420", "450"], "420", ["420"]),
    ("ciudad", "Ciudad", ["Capital Federal", "Rosario", "Resistencia"], "Rosario", ["Rosario"]),
    ("provincia", "Provincia", ["Santa Fe", "Buenos Aires", "Chaco"], "Santa Fe", ["Santa Fe"]),
]
ACE_DOMAINS = {"atencion": ("Atención", 18), "memoria": ("Memoria", 26), "fluencia": ("Fluencia", 14),
               "lenguaje": ("Lenguaje", 26), "visoespacial": ("Visoespacial", 16)}

ACE3 = {
    "code": "ace3",
    "name": "ACE-III – Addenbrooke's Cognitive Examination III",
    "description": "Atención 18, memoria 26, fluencia 14, lenguaje 26 y visoespacial 16. Total 100.",
    "sections": [
        {"title": "Atención", "items": [
            checks("orient_time", "Orientación temporal", ["Año", "Estación", "Mes", "Fecha", "Día"], "atencion",
                   instruction="Pregunte el año, la estación, el mes, la fecha y el día."),
            checks("orient_place", "Orientación espacial", ["País", "Ciudad", "Barrio", "Lugar", "Piso"], "atencion",
                   instruction="Pregunte el país, la ciudad, el barrio, el lugar y el piso."),
            checks("words_register", "Registro de 3 palabras", ["Pelota", "Bandera", "Árbol"], "atencion",
                   instruction="Pida que repita y recuerde: pelota, bandera y árbol."),
            {"key": "serial7", "label": "Restas seriadas", "type": "serial7", "domain": "atencion", "max": 5,
             "instruction": "¿Cuánto es 100 menos 7? Luego siga restando 7. Escriba el número que dice la persona."},
        ]},
        {"title": "Memoria", "items": [
            checks("words_recall", "Recuerdo de las 3 palabras", ["Pelota", "Bandera", "Árbol"], "memoria",
                   instruction="Pida que diga las palabras que repitió antes."),
            checks("address_1", "Nombre y dirección – intento 1", ADDRESS, "memoria", scoring="none",
                   instruction="Pida que repita: Luis Reynal, Pedro Goyena 420, Rosario, Santa Fe. No suma puntos."),
            checks("address_2", "Nombre y dirección – intento 2", ADDRESS, "memoria", scoring="none",
                   instruction="Segundo intento. No suma puntos."),
            checks("address_3", "Nombre y dirección – intento 3", ADDRESS, "memoria",
                   instruction="Tercer intento: cada elemento correcto suma 1 punto."),
            checks("retrograde", "Memoria retrógrada",
                   ["Presidente actual de la Argentina", "Quién descubrió América", "Quién es el Papa",
                    "Presidente de EE. UU. asesinado en los años 60"], "memoria",
                   instruction="Marque las respuestas correctas al día de la evaluación."),
        ]},
        {"title": "Fluencia verbal", "items": [
            {"key": "fluency_p", "label": "Palabras con P", "type": "fluency", "domain": "fluencia", "max": 7,
             "table": FLUENCY_LETTERS_TABLE,
             "instruction": "Un minuto: todas las palabras que comiencen con P, sin nombres ni lugares. "
                            "Anote la cantidad de palabras válidas; el sistema la convierte a puntaje (0 a 7)."},
            {"key": "fluency_animals", "label": "Animales", "type": "fluency", "domain": "fluencia", "max": 7,
             "table": FLUENCY_ANIMALS_TABLE,
             "instruction": "Un minuto: todos los animales posibles. "
                            "Anote la cantidad de animales válidos; el sistema la convierte a puntaje (0 a 7)."},
        ]},
        {"title": "Lenguaje", "items": [
            checks("comprehension", "Lápiz y papel", ["Pone el papel encima del lápiz", "Toma el lápiz pero no el papel",
                   "Le da el lápiz después de tocar el papel"], "lenguaje"),
            checks("writing", "Escritura", ["Hay dos oraciones", "Son sobre el mismo tema", "La gramática es correcta",
                   "La ortografía es correcta"], "lenguaje", scoring="writing",
                   instruction="Pida que escriba al menos dos oraciones narrando algo. Dos oraciones del mismo tema = 1 punto; "
                               "gramática y ortografía correctas = 1 punto extra."),
            checks("repeat_words", "Repetir palabras", ["Hipopótamo", "Excentricidad", "Ininteligible", "Estadístico"],
                   "lenguaje", scoring="repeat_words", instruction="4 correctas = 2 puntos; 3 correctas = 1 punto."),
            # CORRECCIÓN: frases según la planilla y la revisión.
            checks("repeat_phrases", "Repetir frases", ["El flan tiene frutillas y frambuesas",
                   "La orquesta tocó y la audiencia la aplaudió"], "lenguaje"),
            checks("naming", "Denominar dibujos", ["Cuchara", "Libro", "Canguro", "Pingüino", "Ancla", "Camello", "Arpa",
                   "Rinoceronte", "Barril", "Corona", "Cocodrilo", "Acordeón"], "lenguaje"),
            checks("comprehend_pictures", "Comprender dibujos", ["Monarquía", "Antártida", "Marsupial", "Náutica"], "lenguaje",
                   instruction="Señale cuál se asocia con la monarquía, cuál se encuentra en la Antártida, cuál es un marsupial "
                               "y cuál se relaciona con la náutica."),
            checks("irregular_reading", "Lectura de palabras irregulares", ["Jazz", "Lassagna", "Jean", "Hippie", "Jumbo"],
                   "lenguaje", scoring="all", instruction="Las 5 correctas = 1 punto."),
        ]},
        {"title": "Habilidades visoespaciales", "items": [
            # CORRECCIÓN: diagrama infinito superpuesto en lugar de pentágonos.
            choice("infinity", "Copiar el diagrama infinito superpuesto: ¿dibujó dos bucles superpuestos que convergen en un punto o cruz?",
                   [("Sí", 1), ("No", 0)], domain="visoespacial"),
            choice("cube", "Copiar el cubo", [("Tiene 12 líneas", 2), ("No tiene 12 líneas pero mantiene la forma", 1),
                   ("No tiene 12 líneas ni mantiene la forma", 0)], domain="visoespacial"),
            # CORRECCIÓN: "esfera" del reloj.
            choice("clock_face", "Dibujar reloj – esfera", [("Correcta", 1), ("Incorrecta", 0)], domain="visoespacial"),
            choice("clock_numbers", "Dibujar reloj – números", [("Correctos", 2), ("Parcial", 1), ("Incorrectos", 0)], domain="visoespacial"),
            choice("clock_hands", "Dibujar reloj – agujas (cinco y diez)", [("Correctas", 2), ("Parcial", 1), ("Incorrectas", 0)],
                   domain="visoespacial"),
            checks("dots", "Conteo de puntos", ["Cuadrado 1 (8)", "Cuadrado 2 (10)", "Cuadrado 3 (9)", "Cuadrado 4 (7)"],
                   "visoespacial", instruction="Sin señalar con el dedo."),
            checks("letters", "Letras incompletas", ["K", "M", "T", "A"], "visoespacial"),
        ]},
        {"title": "Recuerdo demorado", "items": [
            checks("address_recall", "Recuerdo de nombre y dirección", ADDRESS, "memoria",
                   instruction="«Ahora dígame lo que recuerda del nombre y la dirección que repetíamos al principio.»"),
            {"key": "recognition", "label": "Reconocimiento de nombre y dirección", "type": "recognition", "domain": "memoria",
             "max": 5, "recall_key": "address_recall",
             "instruction": "Lo que ya recordó en el paso anterior suma automáticamente; pregunte solo el resto.",
             "groups": [{"key": key, "label": label, "options": options, "recalled_by": recalled}
                        for key, label, options, _, recalled in RECOGNITION]},
        ]},
    ],
}

SCALES = {scale["code"]: scale for scale in (BARTHEL, GDS15, CQC, ACE3)}


# --- Puntaje -----------------------------------------------------------------


def _items(scale: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for section in scale["sections"] for item in section["items"]]


def item_max(item: dict[str, Any]) -> int:
    if item["type"] == "choice":
        return max(option["points"] for option in item["options"])
    return item["max"]


def fluency_points(table: list[tuple[int, int]], words: int) -> int:
    """Convierte la cantidad de palabras válidas con la tabla de scale_parameters.py."""
    return next((points for minimum, points in table if words >= minimum), 0)


def serial7_points(values: list[Any], *, relative: bool | None = None) -> int:
    """Puntos de las restas seriadas según SERIAL7_RELATIVE_TO_PREVIOUS.

    Relativa: cada resta cuenta si es 7 menos que la respuesta anterior (la primera, desde 100).
    Absoluta: solo cuentan 93, 86, 79, 72 y 65 en su lugar.
    """
    if relative is None:
        relative = SERIAL7_RELATIVE_TO_PREVIOUS
    if not relative:
        expected = [100 - 7 * (index + 1) for index in range(5)]
        return sum(1 for value, right in zip(values[:5], expected) if value == right and not isinstance(value, bool))
    points, previous = 0, 100
    for value in values[:5]:
        if not isinstance(value, int) or isinstance(value, bool):
            previous = None if previous is None else previous - 7
            continue
        if previous is not None and value == previous - 7:
            points += 1
        previous = value
    return points


def _checks_points(item: dict[str, Any], selected: list[str]) -> int:
    count = len(selected)
    rule = item["scoring"]
    if rule == "count":
        return count
    if rule == "all":
        return 1 if count == len(item["items"]) else 0
    if rule == "repeat_words":
        return 2 if count == 4 else 1 if count == 3 else 0
    if rule == "writing":
        base = 1 if {"Hay dos oraciones", "Son sobre el mismo tema"} <= set(selected) else 0
        extra = 1 if {"La gramática es correcta", "La ortografía es correcta"} <= set(selected) else 0
        return base + extra
    return 0


def recognition_points(item: dict[str, Any], answer: dict[str, Any], recalled: list[str]) -> tuple[int, list[str]]:
    """Devuelve el puntaje y los grupos acreditados por el recuerdo previo."""
    points, credited = 0, []
    correct = {key: right for key, _, _, right, _ in RECOGNITION}
    for group in item["groups"]:
        if set(group["recalled_by"]) <= set(recalled):
            points += 1
            credited.append(group["key"])
        elif answer.get(group["key"]) == correct[group["key"]]:
            points += 1
    return points, credited


def score(code: str, answers: dict[str, Any], *, require_complete: bool = True) -> dict[str, Any]:
    """Valida y puntúa. Lanza ValueError con mensaje en español si algo no corresponde."""
    scale = SCALES.get(code)
    if scale is None:
        raise ValueError("Escala desconocida.")
    items = _items(scale)
    known = {item["key"] for item in items}
    if set(answers) - known:
        raise ValueError("Hay respuestas que no corresponden a esta escala.")

    total, maximum, domains, missing, credited = 0, 0, {}, [], []
    for item in items:
        value = answers.get(item["key"])
        kind = item["type"]
        if kind == "choice":
            option = next((o for o in item["options"] if o["value"] == value), None)
            if value is not None and option is None:
                raise ValueError(f"Respuesta inválida en «{item['label']}».")
            if option is None:
                missing.append(item["label"])
            points = option["points"] if option else 0
        elif kind == "checks":
            selected = value or []
            if (
                not isinstance(selected, list)
                or not all(isinstance(entry, str) for entry in selected)
                or not set(selected) <= set(item["items"])
            ):
                raise ValueError(f"Respuesta inválida en «{item['label']}».")
            # Sin repetidos y en el orden de la definición: cada casilla cuenta una vez.
            selected = [label for label in item["items"] if label in set(selected)]
            answers = {**answers, item["key"]: selected}
            points = _checks_points(item, selected)
        elif kind == "serial7":
            values = value or []
            if not isinstance(values, list) or len(values) > 5 or any(
                v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100) for v in values
            ):
                raise ValueError("Revisá los números de las restas seriadas.")
            points = serial7_points(values)
        elif kind == "fluency":
            data = value or {}
            raw = data.get("raw") if isinstance(data, dict) else None
            if not isinstance(data, dict) or (
                raw is not None and (isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 200)
            ):
                raise ValueError(f"Revisá «{item['label']}»: anotá la cantidad de palabras válidas (0 a 200).")
            if raw is None:
                missing.append(item["label"])
                points = 0
                answers = {**answers, item["key"]: {}}
            else:
                # El puntaje lo convierte el servidor; se ignora cualquier puntaje enviado.
                points = fluency_points(item["table"], raw)
                answers = {**answers, item["key"]: {"raw": raw, "score": points}}
        elif kind == "recognition":
            data = value or {}
            if not isinstance(data, dict):
                raise ValueError("Respuesta inválida en el reconocimiento.")
            for group in item["groups"]:
                chosen = data.get(group["key"])
                if chosen is not None and (not isinstance(chosen, str) or chosen not in group["options"]):
                    raise ValueError("Respuesta inválida en el reconocimiento.")
            points, credited = recognition_points(item, data, answers.get(item["recall_key"]) or [])
        else:  # pragma: no cover - definición interna
            raise ValueError("Tipo de ítem desconocido.")

        # Defensa: ningún ítem puede superar su máximo aunque cambie una regla.
        points = max(0, min(points, item_max(item)))
        total += points
        maximum += item_max(item)
        if item.get("domain"):
            bucket = domains.setdefault(item["domain"], {"score": 0, "max": 0})
            bucket["score"] += points
            bucket["max"] += item_max(item)

    if total > maximum:  # pragma: no cover - invariante
        raise ValueError("El puntaje calculado supera el máximo de la escala.")
    if require_complete and missing:
        raise ValueError("Faltan respuestas: " + ", ".join(missing[:5]) + ("…" if len(missing) > 5 else "") + ".")

    labels = {key: label for key, (label, _) in ACE_DOMAINS.items()}
    subscores = {labels.get(key, key): data for key, data in domains.items()} or None
    interpretation = None
    if code == "barthel" and not missing:
        interpretation = next(label for low, high, label in BARTHEL_BANDS if low <= total <= high)
    return {
        "total": total,
        "max": maximum,
        "subscores": subscores,
        "interpretation": interpretation,
        "missing": missing,
        "credited_by_recall": credited,
        "answers": answers,
    }


def public_definitions() -> list[dict[str, Any]]:
    """Definiciones para que la pantalla dibuje cada escala (sin lógica de puntaje)."""
    result = []
    for scale in SCALES.values():
        result.append({**scale, "max": sum(item_max(item) for item in _items(scale))})
    return result
