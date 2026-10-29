"""Offline checks of the DENUE loader and directory tool, using simulated data."""
import csv
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import denue_load, estados, scian, talleres_denue  # noqa: E402


def registro(clee, nombre, lat, lng, clase_id="811111"):
    return {"CLEE": clee, "Id": clee[-4:], "Nombre": nombre, "Clase_actividad": "Reparación",
            "CLASE_ACTIVIDAD_ID": clase_id, "Colonia": "Roma Norte", "Telefono": "5555555555",
            "Correo_e": "x@example.com", "Latitud": str(lat), "Longitud": str(lng)}


@pytest.fixture
def db_con_datos(tmp_path, monkeypatch):
    ruta = tmp_path / "denue.sqlite"
    monkeypatch.setattr(denue_load, "DB", ruta)
    monkeypatch.setattr(talleres_denue, "RUTAS", [ruta])
    monkeypatch.setenv("DENUE_TOKEN", "token-de-prueba")
    monkeypatch.setattr(denue_load.time, "sleep", lambda s: None)
    paginas = {
        "09": [[registro("0900001", "Taller Uno", 19.4195, -99.1627),
                registro("0900002", "Taller Lejano", 19.80, -99.40),
                registro("0900003", "Hojalatería Cercana", 19.4196, -99.1628, "811121"),
                registro("0900004", "Llantera Cercana", 19.4197, -99.1629, "811191"),
                registro("0900005", "Lavado Cercano", 19.4198, -99.1630, "811192")]],
        "15": [[registro("1500001", "Taller Edomex Cercano", 19.4200, -99.1630)]],
    }

    def falso(entidad, inicio, fin, sector, subsector, rama, clase, token):
        assert token == "token-de-prueba"
        paginas_estado = paginas.get(entidad, [])
        indice = (inicio - 1) // denue_load.PAGE
        return paginas_estado[indice] if indice < len(paginas_estado) else []

    monkeypatch.setattr(denue_load, "fetch_page", falso)
    denue_load.main(["--estado", "cdmx"])
    denue_load.main(["--estado", "15"])
    return ruta


def test_resolver_estado():
    assert estados.resolver_estado("cdmx") == "09"
    assert estados.resolver_estado("Ciudad de México") == "09"
    assert estados.resolver_estado("9") == "09"
    assert estados.resolver_estado("veracruz") == "30"
    assert estados.resolver_estado("México") == "15"
    assert estados.resolver_estado("san luis") == "24"
    with pytest.raises(ValueError):
        estados.resolver_estado("narnia")
    with pytest.raises(ValueError):
        estados.resolver_estado("qu")  # Querétaro and Quintana Roo: ambiguous prefixes must not guess


def test_clasificar():
    assert scian.clasificar("811112") == ("mecanica", "electrico")
    assert scian.clasificar("811121") == ("carroceria", "hojalateria_pintura")
    assert scian.clasificar("000000") == ("servicios", "otros")


def test_carga_guarda_registros_por_estado(db_con_datos):
    con = sqlite3.connect(db_con_datos)
    assert con.execute("select count(*) from talleres where entidad='09'").fetchone()[0] == 5
    assert con.execute("select count(*) from talleres where entidad='15'").fetchone()[0] == 1
    assert con.execute("select count(*) from estados").fetchone()[0] == 32


def test_filtro_de_estado_y_sin_contacto(db_con_datos):
    res = talleres_denue.buscar_talleres_directorio("cdmx", 19.4195, -99.1627, radio_km=10)
    assert [r["nombre"] for r in res] == ["Taller Uno", "Llantera Cercana"]  # no Edomex, body shop or wash
    assert not ({"telefono", "correo"} & set(res[0]))
    assert res[0]["registrado"] is False
    otro = talleres_denue.buscar_talleres_directorio("edomex", 19.4195, -99.1627, radio_km=10)
    assert [r["nombre"] for r in otro] == ["Taller Edomex Cercano"]


def test_carroceria_es_opcional(db_con_datos):
    res = talleres_denue.buscar_talleres_directorio(
        "cdmx", 19.4195, -99.1627, radio_km=10, categorias=["mecanica", "llantas", "carroceria"])
    assert "Hojalatería Cercana" in [r["nombre"] for r in res]
    solo = talleres_denue.buscar_talleres_directorio(
        "cdmx", 19.4195, -99.1627, radio_km=10, categorias=["carroceria"])
    assert [r["nombre"] for r in solo] == ["Hojalatería Cercana"]
    esp = talleres_denue.buscar_talleres_directorio(
        "cdmx", 19.4195, -99.1627, radio_km=10, especialidad="llantas")
    assert [r["nombre"] for r in esp] == ["Llantera Cercana"]


def test_carga_desde_csv_latin1(tmp_path, monkeypatch):
    ruta = tmp_path / "denue.sqlite"
    monkeypatch.setattr(denue_load, "DB", ruta)
    columnas = ["id", "clee", "nom_estab", "raz_social", "codigo_act", "nombre_act", "per_ocu", "nom_vial",
                "numero_ext", "nomb_asent", "cod_postal", "cve_ent", "entidad", "municipio", "telefono",
                "correoelec", "www", "latitud", "longitud", "fecha_alta"]

    def fila(clee, nombre, codigo, lat, lng):
        return {"id": clee[-3:], "clee": clee, "nom_estab": nombre, "raz_social": "", "codigo_act": codigo,
                "nombre_act": "x", "per_ocu": "0 a 5", "nom_vial": "CALLE", "numero_ext": "1",
                "nomb_asent": "CENTRO", "cod_postal": "06000", "cve_ent": "09", "entidad": "CIUDAD DE MÉXICO",
                "municipio": "CUAUHTÉMOC", "telefono": "", "correoelec": "", "www": "",
                "latitud": lat, "longitud": lng, "fecha_alta": "2020-01"}

    csv_path = tmp_path / "denue.csv"
    with open(csv_path, "w", encoding="latin-1", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows([fila("0900AAA", "Taller Ñandú", "811111", "19.42", "-99.16"),
                     fila("0900BBB", "Tienda de ropa", "463211", "19.42", "-99.16"),
                     fila("0900CCC", "Hojalatería", "811121", "19.43", "-99.17")])
    denue_load.main(["--csv", str(csv_path)])
    con = sqlite3.connect(ruta)
    assert con.execute("select count(*) from talleres").fetchone()[0] == 2  # non-8111 row skipped
    assert con.execute("select nombre, entidad, categoria from talleres where clee='0900AAA'").fetchone() == (
        "Taller Ñandú", "09", "mecanica")


def test_descarga_masiva_por_estado(tmp_path, monkeypatch):
    """The bulk loader downloads, extracts, loads and cleans up; here with a fake zip."""
    import io
    import zipfile as zf

    from tools import denue_bulk

    columnas = ["id", "clee", "nom_estab", "raz_social", "codigo_act", "nombre_act", "per_ocu", "nom_vial",
                "numero_ext", "nomb_asent", "cod_postal", "cve_ent", "entidad", "municipio", "telefono",
                "correoelec", "www", "latitud", "longitud", "fecha_alta"]
    filas = [{"id": "1", "clee": "05000AAA", "nom_estab": "Taller Saltillo", "raz_social": "", "codigo_act": "811111",
              "nombre_act": "x", "per_ocu": "0 a 5", "nom_vial": "C", "numero_ext": "1", "nomb_asent": "CENTRO",
              "cod_postal": "25000", "cve_ent": "05", "entidad": "COAHUILA", "municipio": "SALTILLO",
              "telefono": "", "correoelec": "", "www": "", "latitud": "25.42", "longitud": "-101.0",
              "fecha_alta": "2020-01"}]
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=columnas, quoting=csv.QUOTE_ALL)
    escritor.writeheader()
    escritor.writerows(filas)
    zip_falso = tmp_path / "falso.zip"
    with zf.ZipFile(zip_falso, "w") as z:
        z.writestr("conjunto_de_datos/denue_inegi_05_.csv", texto.getvalue().encode("latin-1"))
        z.writestr("diccionario_de_datos/dic.csv", "x")

    monkeypatch.setattr(denue_load, "DB", tmp_path / "denue.sqlite")
    pedidos = []
    monkeypatch.setattr(denue_bulk, "descargar", lambda cve, destino, parte=None: pedidos.append(parte or cve) or zip_falso)
    denue_bulk.main(["--estado", "coahuila"])
    con = sqlite3.connect(tmp_path / "denue.sqlite")
    assert con.execute("select nombre, entidad from talleres").fetchall() == [("Taller Saltillo", "05")]

    # A state published in two files downloads both parts and adds up their rows.
    monkeypatch.setitem(denue_bulk.PARTES, "05", ["05_1", "05_2"])
    assert denue_bulk.archivos_de("05") == ["05_1", "05_2"] and denue_bulk.archivos_de("09") == ["09"]
    assert denue_bulk.archivos_de("15") == ["15_1", "15_2"]
    pedidos.clear()
    assert denue_bulk.cargar_estado(sqlite3.connect(tmp_path / "denue.sqlite"), "05") == 2
    assert pedidos == ["05_1", "05_2"]


def test_archivos_de_produccion_por_estado(db_con_datos, tmp_path, monkeypatch):
    """Production reads one slim file per state, with no contact columns."""
    from tools import build_prod_data

    destino = tmp_path / "prod"
    origen = sqlite3.connect(db_con_datos)
    assert build_prod_data.construir(origen, "09", destino) == 5
    assert build_prod_data.construir(origen, "15", destino) == 1
    cols = [c[1] for c in sqlite3.connect(destino / "denue_09.sqlite").execute("pragma table_info(talleres)")]
    assert not ({"telefono", "correo", "sitio", "razon_social"} & set(cols))

    monkeypatch.setattr(talleres_denue, "RUTAS", [tmp_path / "no_hay_base_de_desarrollo.sqlite"])
    monkeypatch.setattr(talleres_denue, "DIR_PROD", destino)
    assert talleres_denue.estados_con_datos() == {"09", "15"}
    res = talleres_denue.buscar_talleres_directorio("cdmx", 19.4195, -99.1627, radio_km=10)
    assert [r["nombre"] for r in res] == ["Taller Uno", "Llantera Cercana"]
    with pytest.raises(FileNotFoundError):
        talleres_denue.buscar_talleres_directorio("jalisco", 20.66, -103.35)
