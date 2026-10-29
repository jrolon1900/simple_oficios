"""Agent that books an appointment with a mechanic."""
import json
from datetime import datetime
from pathlib import Path

from strands import Agent, tool

from config import get_model

CITAS = Path(__file__).resolve().parent.parent / "data" / "citas.json"

SYSTEM_PROMPT = (
    "Agendas citas con mecánicos. Usa crear_cita con el id del mecánico, el cliente y la fecha/hora. "
    "Confirma en español con un resumen corto."
)


@tool
def crear_cita(mecanico_id: int, cliente: str, fecha_hora: str, problema: str) -> dict:
    """Guarda una cita con un mecánico.

    Args:
        mecanico_id: id del mecánico elegido.
        cliente: nombre del cliente.
        fecha_hora: fecha y hora propuesta (texto libre, por ejemplo 2026-11-02 10:00).
        problema: resumen del problema del vehículo.
    """
    citas = json.loads(CITAS.read_text(encoding="utf-8")) if CITAS.exists() else []
    cita = {
        "id": len(citas) + 1,
        "mecanico_id": mecanico_id,
        "cliente": cliente,
        "fecha_hora": fecha_hora,
        "problema": problema,
        "creada": datetime.now().isoformat(timespec="seconds"),
    }
    citas.append(cita)
    CITAS.write_text(json.dumps(citas, ensure_ascii=False, indent=2), encoding="utf-8")
    return cita


@tool
def agendar_cita(mecanico_id: int, cliente: str, fecha_hora: str, problema: str) -> str:
    """Agenda una cita con un mecánico y devuelve la confirmación.

    Args:
        mecanico_id: id del mecánico elegido.
        cliente: nombre del cliente.
        fecha_hora: fecha y hora propuesta.
        problema: resumen del problema del vehículo.
    """
    agent = Agent(model=get_model(), tools=[crear_cita], system_prompt=SYSTEM_PROMPT)
    return str(agent(f"Mecánico {mecanico_id}, cliente {cliente}, fecha {fecha_hora}, problema: {problema}"))
