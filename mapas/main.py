"""Servicio "mapas": directorio de talleres, ranking y agentes.

Vercel lo sirve bajo /api/mapas (ver vercel.json en la raíz) y entrega la ruta original, por eso
todas las rutas llevan ese prefijo. Local: desde mapas/, `uvicorn main:app --reload`.
"""
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import APIRouter, FastAPI, HTTPException, Query  # noqa: E402
from fastapi.responses import FileResponse, RedirectResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from tools.estados import CAPITALES, ESTADOS, resolver_estado  # noqa: E402

PREFIJO = "/api/mapas"
app = FastAPI(title="Simple Oficios · mapas")
router = APIRouter(prefix=PREFIJO)


class Solicitud(BaseModel):
    mensaje: str
    lat: float
    lng: float


@lru_cache
def orquestador():
    """Built on first use, so health and directory routes work without an LLM key."""
    from agents.orquestador import crear_orquestador
    return crear_orquestador()


@app.get("/", include_in_schema=False)
def raiz():
    """The site root opens the demo, so the bare Vercel link is useful on its own."""
    return RedirectResponse(f"{PREFIJO}/demo")


@router.get("/demo", include_in_schema=False)
def demo():
    """Demo page (map and directory search) to see the service working."""
    return FileResponse(Path(__file__).resolve().parent / "static" / "demo.html")


@router.get("/health")
def health():
    return {"ok": True, "servicio": "mapas"}


@router.get("/estados")
def estados():
    """The 32 states with a map center (their capital) and whether shops are loaded for them."""
    from tools.talleres_denue import estados_con_datos
    con_datos = estados_con_datos()
    return [{"cve": cve, "nombre": nombre, "lat": CAPITALES[cve][0], "lng": CAPITALES[cve][1],
             "con_datos": cve in con_datos} for cve, nombre in ESTADOS.items()]


@router.get("/talleres")
def talleres(estado: str, lat: float, lng: float,
             radio_km: float = Query(5, gt=0, le=50), limite: int = Query(10, ge=1, le=50),
             categorias: str | None = Query(None, description="mecanica,llantas,carroceria,servicios"),
             especialidad: str | None = None):
    """Directorio de talleres no registrados (INEGI DENUE), filtrado por estado."""
    try:
        resolver_estado(estado)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from tools.talleres_denue import buscar_talleres_directorio
    lista = [c.strip() for c in categorias.split(",") if c.strip()] if categorias else None
    try:
        return buscar_talleres_directorio(estado=estado, lat=lat, lng=lng, radio_km=radio_km,
                                          limite=limite, categorias=lista, especialidad=especialidad)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Datos del directorio no disponibles en este entorno")


@router.post("/solicitud")
def solicitud(s: Solicitud):
    try:
        agente = orquestador()
    except KeyError as e:
        raise HTTPException(status_code=503, detail=f"Falta configurar el modelo: {e}")
    respuesta = agente(f"{s.mensaje}\n(Ubicación del cliente: lat {s.lat}, lng {s.lng})")
    return {"respuesta": str(respuesta)}


app.include_router(router)
