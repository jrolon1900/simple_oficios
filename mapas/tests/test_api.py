"""Checks of the HTTP surface of the mapas service (no LLM key needed)."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from tools import talleres_denue  # noqa: E402


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    ruta = tmp_path / "prod.sqlite"
    con = sqlite3.connect(ruta)
    con.execute("create table talleres (clee text, nombre text, clase text, categoria text, especialidad text, "
                "entidad text, colonia text, lat real, lng real)")
    con.executemany("insert into talleres values (?,?,?,?,?,?,?,?,?)", [
        ("1", "Taller Uno", "Mecánica", "mecanica", "mecanica_general", "09", "Roma", 19.4195, -99.1627),
        ("2", "Hojalatería Dos", "Hojalatería", "carroceria", "hojalateria_pintura", "09", "Roma", 19.4196, -99.1628),
    ])
    con.commit()
    con.close()
    monkeypatch.setattr(talleres_denue, "RUTAS", [ruta])
    monkeypatch.setattr(talleres_denue, "DIR_PROD", tmp_path / "sin_archivos_de_produccion")
    return TestClient(main.app)


def test_health_y_estados(cliente):
    assert cliente.get("/api/mapas/health").json() == {"ok": True, "servicio": "mapas"}
    estados = cliente.get("/api/mapas/estados").json()
    assert len(estados) == 32
    por_cve = {e["cve"]: e for e in estados}
    assert por_cve["09"]["nombre"] == "Ciudad de México" and por_cve["09"]["con_datos"] is True
    assert por_cve["05"]["con_datos"] is False  # only the states loaded in the database say True
    assert all(14 < e["lat"] < 33 and -118 < e["lng"] < -86 for e in estados)  # centers fall in Mexico


def test_las_rutas_solo_existen_bajo_el_prefijo(cliente):
    assert cliente.get("/health").status_code == 404


def test_talleres_por_estado_y_carroceria_opcional(cliente):
    base = {"estado": "cdmx", "lat": 19.4195, "lng": -99.1627, "radio_km": 5}
    nombres = [t["nombre"] for t in cliente.get("/api/mapas/talleres", params=base).json()]
    assert nombres == ["Taller Uno"]
    con = cliente.get("/api/mapas/talleres", params={**base, "categorias": "mecanica,carroceria"}).json()
    assert {t["nombre"] for t in con} == {"Taller Uno", "Hojalatería Dos"}
    assert not any("telefono" in t or "correo" in t for t in con)


def test_estado_invalido_y_datos_no_disponibles(cliente, monkeypatch):
    params = {"estado": "narnia", "lat": 19.4, "lng": -99.1}
    assert cliente.get("/api/mapas/talleres", params=params).status_code == 422
    monkeypatch.setattr(talleres_denue, "RUTAS", [Path("/no/existe.sqlite")])
    ok = {"estado": "cdmx", "lat": 19.4, "lng": -99.1}
    assert cliente.get("/api/mapas/talleres", params=ok).status_code == 503


def test_solicitud_sin_modelo_configurado_responde_503(cliente, monkeypatch):
    for var in ("LLM_API_KEY", "FREELLM_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    main.orquestador.cache_clear()
    r = cliente.post("/api/mapas/solicitud", json={"mensaje": "me falla el freno", "lat": 19.4, "lng": -99.1})
    assert r.status_code == 503


def test_pagina_demo(cliente):
    r = cliente.get("/api/mapas/demo")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "OpenStreetMap contributors" in r.text and "/estados" in r.text


def test_la_raiz_lleva_a_la_demo(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/api/mapas/demo"
