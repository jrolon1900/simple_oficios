"""Tools over the (simulated) mechanics database."""
import json
import math
from pathlib import Path

from strands import tool

DATA = Path(__file__).resolve().parent.parent / "data"


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlng = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


@tool
def buscar_mecanicos_cercanos(especialidad: str, lat: float, lng: float, radio_km: float = 10) -> list[dict]:
    """Busca mecánicos registrados con una especialidad, ordenados por distancia.

    Args:
        especialidad: frenos, motor, electrico, suspension, llantas o aire_acondicionado.
        lat: latitud del usuario.
        lng: longitud del usuario.
        radio_km: radio máximo de búsqueda en kilómetros.
    """
    mecanicos = json.loads((DATA / "mecanicos.json").read_text(encoding="utf-8"))
    encontrados = []
    for m in mecanicos:
        if especialidad.lower() not in m["especialidades"]:
            continue
        distancia = _km(lat, lng, m["lat"], m["lng"])
        if distancia <= radio_km:
            encontrados.append({**m, "distancia_km": round(distancia, 2)})
    return sorted(encontrados, key=lambda m: m["distancia_km"])
