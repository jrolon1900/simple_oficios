"""Build the slim per-state DENUE files that ship to production (no phone, email or website).

The development database keeps every column and every state; production only needs what the
directory tool returns, so contact data stays out of the repository. One file per state keeps each
one small (about 1 to 4 MB) and lets a request open only the state it asks for.

Run from mapas/:
    python tools/build_prod_data.py              # the states in ESTADOS_PRODUCCION (CDMX for now)
    python tools/build_prod_data.py 09 05        # only these state codes
    python tools/build_prod_data.py todos        # every state present in the development database
"""
import sqlite3
import sys
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "data"
ORIGEN = DATOS / "denue" / "denue_talleres.sqlite"
DESTINO = DATOS / "prod"

COLUMNAS = "clee, nombre, clase, categoria, especialidad, entidad, colonia, lat, lng"
# States that ship to production. Pilot: CDMX only; add a code here when its data is ready to deploy.
ESTADOS_PRODUCCION = ("09",)


def construir(src: sqlite3.Connection, cve: str, destino: Path = DESTINO) -> int:
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"denue_{cve}.sqlite"
    ruta.unlink(missing_ok=True)
    filas = src.execute(f"select {COLUMNAS} from talleres where entidad = ?", (cve,)).fetchall()
    out = sqlite3.connect(ruta)
    out.execute("create table talleres (clee text primary key, nombre text, clase text, categoria text, "
                "especialidad text, entidad text, colonia text, lat real, lng real)")
    out.executemany("insert into talleres values (?,?,?,?,?,?,?,?,?)", filas)
    out.execute("create index talleres_entidad_lat on talleres (entidad, lat)")
    out.commit()
    out.execute("vacuum")
    out.close()
    return len(filas)


def main(argv=None) -> None:
    if not ORIGEN.exists():
        raise SystemExit(f"Falta {ORIGEN}; cárgala con tools/denue_bulk.py o tools/denue_load.py")
    src = sqlite3.connect(f"file:{ORIGEN}?mode=ro", uri=True)
    pedidas = list(argv if argv is not None else sys.argv[1:])
    if pedidas == ["todos"]:
        claves = [f[0] for f in src.execute("select distinct entidad from talleres order by 1")]
    else:
        claves = pedidas or list(ESTADOS_PRODUCCION)
    total = 0
    for cve in claves:
        n = construir(src, cve)
        total += n
        print(f"{cve}: {n} talleres ({(DESTINO / f'denue_{cve}.sqlite').stat().st_size / 1e6:.1f} MB)")
    print(f"{len(claves)} estados, {total} talleres")


if __name__ == "__main__":
    main()
