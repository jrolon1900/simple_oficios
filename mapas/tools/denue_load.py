"""Load INEGI DENUE car-repair establishments (SCIAN 8111) into SQLite.

Two sources, same table:
  1. Bulk CSV from INEGI's "Descarga masiva" (no token needed):
       python tools/denue_load.py --csv path/to/denue_inegi_09_.csv
  2. The API, one state at a time (needs DENUE_TOKEN in the environment, never as an argument):
       python tools/denue_load.py --estado cdmx        # or a code/name, or 'todos'
       python tools/denue_load.py --estado cdmx --max-pages 1   # quick check

Run from simple_oficios/. The API defaults filter sector 81 / subsector 811 / rama 8111;
pass --rama 0 to load every activity (not recommended).
"""
import argparse
import csv
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.estados import ESTADOS, resolver_estado  # noqa: E402
from tools.scian import clasificar  # noqa: E402

BASE = "https://www.inegi.org.mx/app/api/denue/v1/consulta/BuscarAreaAct"
PAGE = 100
DB = Path(__file__).resolve().parent.parent / "data" / "denue" / "denue_talleres.sqlite"

COLUMNS = ("clee", "id", "nombre", "razon_social", "clase_id", "clase", "categoria", "especialidad",
           "estrato", "entidad", "calle", "num_ext", "colonia", "cp", "ubicacion", "telefono",
           "correo", "sitio", "lat", "lng", "fecha_alta", "cargado_en")

SCHEMA = f"""
create table if not exists estados (cve text primary key, nombre text not null);
create table if not exists talleres (
  clee text primary key, id text, nombre text, razon_social text,
  clase_id text, clase text, categoria text, especialidad text, estrato text, entidad text,
  calle text, num_ext text, colonia text, cp text, ubicacion text,
  telefono text, correo text, sitio text,
  lat real, lng real, fecha_alta text, cargado_en text
);
create index if not exists talleres_entidad_lat on talleres (entidad, lat);
create index if not exists talleres_categoria on talleres (entidad, categoria);
"""
INSERT = f"insert or replace into talleres ({','.join(COLUMNS)}) values ({','.join('?' * len(COLUMNS))})"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row(clee, ident, nombre, razon, clase_id, clase, estrato, entidad, calle, num_ext, colonia, cp,
         ubicacion, telefono, correo, sitio, lat, lng, fecha_alta) -> tuple:
    categoria, especialidad = clasificar(clase_id)
    return (clee, ident, nombre, razon, clase_id, clase, categoria, especialidad, estrato, entidad,
            calle, num_ext, colonia, cp, ubicacion, telefono, correo, sitio,
            _float(lat), _float(lng), fecha_alta, datetime.now(timezone.utc).isoformat(timespec="seconds"))


def api_row(d: dict, entidad: str) -> tuple:
    return _row(d.get("CLEE"), d.get("Id"), d.get("Nombre"), d.get("Razon_social"),
                d.get("CLASE_ACTIVIDAD_ID"), d.get("Clase_actividad"), d.get("Estrato"), entidad,
                d.get("Calle"), d.get("Num_Exterior"), d.get("Colonia"), d.get("CP"), d.get("Ubicacion"),
                d.get("Telefono"), d.get("Correo_e"), d.get("Sitio_internet"),
                d.get("Latitud"), d.get("Longitud"), d.get("Fecha_Alta"))


def csv_row(d: dict) -> tuple:
    return _row(d["clee"], d["id"], d["nom_estab"], d["raz_social"], d["codigo_act"].strip(),
                d["nombre_act"].strip(), d["per_ocu"], d["cve_ent"].strip().zfill(2),
                d["nom_vial"], d["numero_ext"], d["nomb_asent"], d["cod_postal"],
                f"{d['municipio']}, {d['entidad']}", d["telefono"], d["correoelec"], d["www"],
                d["latitud"], d["longitud"], d["fecha_alta"])


def load_csv(db: sqlite3.Connection, path: str) -> int:
    """Load a DENUE bulk CSV, keeping only SCIAN 8111. The file may be latin-1 or utf-8."""
    encoding = "utf-8-sig"
    try:
        with open(path, encoding=encoding) as f:
            f.read(2_000_000)
    except UnicodeDecodeError:
        encoding = "latin-1"
    total, lote = 0, []
    with open(path, encoding=encoding, newline="") as f:
        for d in csv.DictReader(f):
            if not d["codigo_act"].strip().startswith("8111") or not d.get("clee"):
                continue
            lote.append(csv_row(d))
            if len(lote) >= 5000:
                db.executemany(INSERT, lote)
                total += len(lote)
                lote = []
    if lote:
        db.executemany(INSERT, lote)
        total += len(lote)
    db.commit()
    return total


def fetch_page(entidad: str, inicio: int, fin: int, sector: str, subsector: str,
               rama: str, clase: str, token: str) -> list[dict]:
    """One API page. Errors never include the URL, because the token is part of it."""
    url = f"{BASE}/{entidad}/0/0/0/0/{sector}/{subsector}/{rama}/{clase}/0/{inicio}/{fin}/0/{token}"
    for intento in range(4):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "simple-oficios-hackathon"})
        except requests.RequestException as e:
            error = type(e).__name__
        else:
            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError:
                    return []
                return data if isinstance(data, list) else []
            error = f"HTTP {r.status_code}"
        time.sleep(2 ** intento)
    raise RuntimeError(f"DENUE request failed for state {entidad}, records {inicio}-{fin}: {error}")


def load_state(db: sqlite3.Connection, entidad: str, token: str, sector: str, subsector: str,
               rama: str, clase: str, max_pages: int | None = None) -> int:
    total, pagina = 0, 0
    while max_pages is None or pagina < max_pages:
        inicio = pagina * PAGE + 1
        rows = fetch_page(entidad, inicio, inicio + PAGE - 1, sector, subsector, rama, clase, token)
        if not rows:
            break
        db.executemany(INSERT, [api_row(d, entidad) for d in rows if d.get("CLEE")])
        db.commit()
        total += len(rows)
        pagina += 1
        print(f"  {ESTADOS[entidad]}: {total} registros", flush=True)
        if len(rows) < PAGE:
            break
        time.sleep(0.5)
    return total


def main(argv=None) -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", help="DENUE bulk CSV from INEGI (no token needed)")
    p.add_argument("--estado", help="API: código, nombre, 'cdmx' o 'todos'")
    p.add_argument("--sector", default="81")
    p.add_argument("--subsector", default="811")
    p.add_argument("--rama", default="8111")
    p.add_argument("--clase", default="0")
    p.add_argument("--max-pages", type=int, default=None)
    args = p.parse_args(argv)
    if not args.csv and not args.estado:
        p.error("indica --csv o --estado")

    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    db.executemany("insert or replace into estados values (?,?)", list(ESTADOS.items()))

    if args.csv:
        print(f"{load_csv(db, args.csv)} talleres cargados desde el CSV")
    else:
        token = os.getenv("DENUE_TOKEN")
        if not token:
            raise SystemExit("Falta DENUE_TOKEN en el entorno o en el .env")
        entidades = list(ESTADOS) if args.estado.lower() == "todos" else [resolver_estado(args.estado)]
        for e in entidades:
            print(f"{e} {ESTADOS[e]}", flush=True)
            load_state(db, e, token, args.sector, args.subsector, args.rama, args.clase, args.max_pages)
    db.close()


if __name__ == "__main__":
    main()
