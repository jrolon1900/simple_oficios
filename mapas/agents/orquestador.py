"""Orchestrator: coordinates the specialist agents (agents-as-tools pattern)."""
from strands import Agent

from agents.agenda import agendar_cita
from agents.diagnostico import diagnosticar_problema
from agents.matching import encontrar_mecanicos
from config import get_model

SYSTEM_PROMPT = (
    "Eres el asistente de una plataforma que conecta clientes con mecánicos confiables. "
    "Flujo: 1) diagnosticar_problema con lo que cuenta el cliente; 2) encontrar_mecanicos con la "
    "especialidad y las coordenadas; 3) si el cliente elige uno, agendar_cita. "
    "No agendes sin que el cliente haya elegido mecánico y horario. Responde siempre en español."
)


def crear_orquestador() -> Agent:
    return Agent(
        model=get_model(),
        tools=[diagnosticar_problema, encontrar_mecanicos, agendar_cita],
        system_prompt=SYSTEM_PROMPT,
    )
