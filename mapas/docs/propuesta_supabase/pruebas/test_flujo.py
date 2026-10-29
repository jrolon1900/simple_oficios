"""End-to-end checks of the data model and its row level security, as real users.

Run from simple_oficios/: python -m pytest pruebas -v   (after seed_usuarios.py)
"""
from datetime import datetime, timedelta, timezone

import pytest
import supa

CENTRO_CDMX = {"p_lat": 19.4326, "p_lng": -99.1332}


@pytest.fixture(scope="module")
def u():
    sesiones = {clave: supa.sesion(clave) for clave in supa.USUARIOS}
    yield sesiones
    ids = [sesiones["cliente1"][1], sesiones["cliente2"][1]]
    supa.admin().table("appointments").delete().in_("client_id", ids).execute()


def test_busqueda_por_especialidad(u):
    cli, _ = u["cliente1"]
    rows = cli.rpc("search_mechanics", {**CENTRO_CDMX, "p_specialty": "frenos", "p_radius_km": 15}).execute().data
    assert [r["shop_name"] for r in rows] == ["Taller El Pistón"]
    assert "phone" not in rows[0]


def test_puertas_de_calidad(u):
    cli, _ = u["cliente1"]
    args = {**CENTRO_CDMX, "p_specialty": "llantas", "p_radius_km": 20}
    assert len(cli.rpc("search_mechanics", args).execute().data) == 1
    assert cli.rpc("search_mechanics", {**args, "p_min_rating": 4.5}).execute().data == []


def test_ranking_bayesiano_prefiere_volumen(u):
    cli, _ = u["cliente1"]
    rows = cli.rpc("search_mechanics", {**CENTRO_CDMX, "p_specialty": "suspension", "p_radius_km": 20}).execute().data
    assert [r["shop_name"] for r in rows] == ["Taller El Pistón", "Llantas Iztapalapa"]


def test_contacto_oculto(u):
    cli, _ = u["cliente1"]
    _, mec_id = u["mecanico1"]
    assert cli.table("profiles").select("phone").eq("id", mec_id).execute().data == []


def test_flujo_cita_completo(u):
    cli, cli_id = u["cliente1"]
    cli2, cli2_id = u["cliente2"]
    mec, mec_id = u["mecanico1"]
    otro_mec, _ = u["mecanico2"]

    fecha = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    cita = cli.table("appointments").insert({
        "client_id": cli_id, "mechanic_id": mec_id,
        "issue_description": "Mi carro hace ruido al frenar",
        "vehicle_make": "Nissan", "vehicle_model": "Versa", "vehicle_year": 2018,
        "appointment_at": fecha, "status": "pending",
        "specialty": "frenos", "urgency": "medium", "client_area": "Cuauhtémoc",
    }).execute().data[0]
    assert cita["status"] == "pending"

    # Only the involved parties can see it.
    assert len(mec.table("appointments").select("id").eq("id", cita["id"]).execute().data) == 1
    assert otro_mec.table("appointments").select("id").eq("id", cita["id"]).execute().data == []
    assert cli2.table("appointments").select("id").eq("id", cita["id"]).execute().data == []

    # A client cannot create an appointment on behalf of someone else.
    with pytest.raises(Exception):
        cli2.table("appointments").insert({
            "client_id": cli_id, "mechanic_id": mec_id, "issue_description": "x",
            "appointment_at": fecha, "status": "pending",
        }).execute()

    # Only the assigned mechanic can answer.
    with pytest.raises(Exception):
        cli.rpc("respond_appointment", {"p_appointment_id": cita["id"], "p_approve": True}).execute()
    with pytest.raises(Exception):
        otro_mec.rpc("respond_appointment", {"p_appointment_id": cita["id"], "p_approve": True}).execute()

    r = mec.rpc("respond_appointment", {"p_appointment_id": cita["id"], "p_approve": True}).execute().data
    r = r[0] if isinstance(r, list) else r
    assert r["status"] == "approved"
    assert cli.table("appointments").select("status").eq("id", cita["id"]).execute().data[0]["status"] == "approved"

    # Post-appointment: each side files its own report; nobody can sign for the other side.
    cli.table("appointment_reports").insert({
        "appointment_id": cita["id"], "author_id": cli_id, "author_role": "client", "attended": True,
        "amount_mxn": 1200, "satisfaction": 5, "recommendation": "Rápido y honesto",
    }).execute()
    with pytest.raises(Exception):
        mec.table("appointment_reports").insert({
            "appointment_id": cita["id"], "author_id": mec_id, "author_role": "client", "attended": True,
        }).execute()
    mec.table("appointment_reports").insert({
        "appointment_id": cita["id"], "author_id": mec_id, "author_role": "mechanic", "attended": True,
    }).execute()

    assert len(mec.table("appointment_reports").select("id").eq("appointment_id", cita["id"]).execute().data) == 2
    assert cli2.table("appointment_reports").select("id").eq("appointment_id", cita["id"]).execute().data == []
