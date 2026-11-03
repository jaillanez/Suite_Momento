"""Parámetros editables de las escalas.

Este archivo reúne los valores que el equipo profesional puede querer ajustar sin
tocar la lógica de puntaje. Cada valor indica de dónde sale. Después de cambiarlo,
correr las pruebas (`pytest`) y reiniciar la API. Las evaluaciones ya guardadas no se
recalculan: conservan el puntaje con el que se cargaron.

Detalle y fuentes en docs/escalas.md.
"""

from __future__ import annotations

# --- Barthel -----------------------------------------------------------------

# Puntos de "Comer". La planilla daba 15 a "Independiente" (el total llegaba a 105).
# El índice de Barthel original usa 10; verificado en documentos oficiales (Ministerio
# de Inclusión de Ecuador, Junta de Andalucía).
BARTHEL_EATING = [("Incapaz", 0), ("Necesita ayuda", 5), ("Independiente", 10)]

# Rangos de interpretación: (desde, hasta, texto). Son los de la planilla del equipo;
# 100 = "Independiente" coincide con todas las fuentes consultadas. Otras fuentes usan
# cortes distintos (0-20 / 21-60 / 61-90 / 91-99 / 100). Deben cubrir de 0 a 100 sin huecos.
BARTHEL_BANDS = [
    (0, 24, "Dependencia total"),
    (25, 49, "Dependencia severa"),
    (50, 74, "Dependencia moderada"),
    (75, 90, "Dependencia media"),
    (91, 99, "Dependencia mínima"),
    (100, 100, "Independiente"),
]

# --- ACE-III -----------------------------------------------------------------

# Restas seriadas. True: cada resta cuenta si es 7 menos que la respuesta anterior,
# aunque esa estuviera mal (guía oficial ACE-III 2017: "92, 85, 79, 72, 65 – score = 3").
# False: solo cuentan los resultados exactos 93, 86, 79, 72 y 65.
SERIAL7_RELATIVE_TO_PREVIOUS = True

# Fluencia: (mínimo de palabras válidas, puntaje). Se usa la primera fila que se cumple.
# Fuente: ACE-III 2017, versión A (FRONTIER). Si el equipo usa la adaptación argentina
# con otros cortes, se cambian acá.
FLUENCY_LETTERS_TABLE = [(18, 7), (14, 6), (11, 5), (8, 4), (6, 3), (4, 2), (2, 1), (0, 0)]
FLUENCY_ANIMALS_TABLE = [(22, 7), (17, 6), (14, 5), (11, 4), (9, 3), (7, 2), (5, 1), (0, 0)]
