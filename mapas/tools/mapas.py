"""Optional Google Maps tools (Places API New). Needs GOOGLE_MAPS_API_KEY."""
import os

import requests
from strands import tool


@tool
def buscar_talleres_google(lat: float, lng: float, radio_m: int = 5000) -> list[dict]:
    """Busca talleres mecánicos externos cerca de unas coordenadas usando Google Places.

    Args:
        lat: latitud del usuario.
        lng: longitud del usuario.
        radio_m: radio de búsqueda en metros.
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        return [{"error": "GOOGLE_MAPS_API_KEY no configurada"}]
    r = requests.post(
        "https://places.googleapis.com/v1/places:searchNearby",
        headers={
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.location",
        },
        json={
            "includedTypes": ["car_repair"],
            "maxResultCount": 10,
            "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radio_m)}},
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("places", [])
