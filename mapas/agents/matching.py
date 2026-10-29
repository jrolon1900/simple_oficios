"""Agent that picks the best mechanics for a diagnosis and a location."""
from strands import Agent, tool

from config import get_model
from tools.mapas import buscar_talleres_google
from tools.mecanicos_db import buscar_mecanicos_cercanos

SYSTEM_PROMPT = (
    "Recomiendas mecánicos. Usa buscar_mecanicos_cercanos con la especialidad y las coordenadas dadas. "
    "Usa buscar_talleres_google solo si no hay resultados registrados. "
    "Responde en español con los 3 mejores: nombre, distancia, rating y teléfono."
)


@tool
def encontrar_mecanicos(especialidad: str, lat: float, lng: float) -> str:
    """Encuentra y recomienda mecánicos para una especialidad cerca de unas coordenadas.

    Args:
        especialidad: especialidad requerida (frenos, motor, electrico...).
        lat: latitud del usuario.
        lng: longitud del usuario.
    """
    agent = Agent(
        model=get_model(),
        tools=[buscar_mecanicos_cercanos, buscar_talleres_google],
        system_prompt=SYSTEM_PROMPT,
    )
    return str(agent(f"Especialidad: {especialidad}. Ubicación: lat {lat}, lng {lng}."))
