"""Agent that classifies the user's car problem."""
from strands import Agent, tool

from config import get_model

SYSTEM_PROMPT = (
    "Eres un mecánico experto. A partir de la descripción del usuario responde SOLO con: "
    "especialidad (frenos, motor, electrico, suspension, llantas o aire_acondicionado), "
    "urgencia (baja, media o alta) y una explicación breve en español."
)


@tool
def diagnosticar_problema(descripcion: str) -> str:
    """Clasifica un problema del vehículo en especialidad y urgencia.

    Args:
        descripcion: lo que el usuario cuenta que le pasa al carro.
    """
    agent = Agent(model=get_model(), system_prompt=SYSTEM_PROMPT)
    return str(agent(descripcion))
