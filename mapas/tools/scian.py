"""SCIAN México 2023, rama 8111 (car and truck repair): code -> category and specialty.

Verified against INEGI's official SCIAN catalog and the DENUE CDMX file (05/2026).
Categories: "mecanica" and "llantas" are searched by default; "carroceria" (body shops) is an
option; "servicios" (wash, lube, other) is stored but only returned when asked for.
DENUE cannot tell "frenos" or "motor repair" apart: brakes fall inside 811111.
"""

CLASES = {
    "811111": ("mecanica", "mecanica_general"),    # Reparación mecánica en general
    "811112": ("mecanica", "electrico"),           # Sistema eléctrico y electrónico
    "811113": ("mecanica", "motor"),               # Rectificación de partes de motor
    "811114": ("mecanica", "transmision"),         # Transmisiones
    "811115": ("mecanica", "suspension"),          # Suspensiones
    "811116": ("mecanica", "alineacion_balanceo"),
    "811119": ("mecanica", "otras_mecanicas"),
    "811121": ("carroceria", "hojalateria_pintura"),
    "811122": ("carroceria", "tapiceria"),
    "811123": ("carroceria", "blindaje"),
    "811129": ("carroceria", "cristales_carroceria"),
    "811191": ("llantas", "llantas"),              # Reparación menor de llantas
    "811192": ("servicios", "lavado_lubricado"),
    "811199": ("servicios", "otros"),
}

CATEGORIAS_POR_DEFECTO = ("mecanica", "llantas")


def clasificar(codigo: str) -> tuple[str, str]:
    """(category, specialty) for a six-digit SCIAN code; unknown codes go to "servicios"."""
    return CLASES.get(str(codigo).strip(), ("servicios", "otros"))
