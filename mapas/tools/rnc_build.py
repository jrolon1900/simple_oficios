"""Build a compact national routing database from INEGI's Red Nacional de Caminos 2025.

The source GeoPackage (2+ GB) is opened read-only and treated as untrusted data.
Output: a SQLite file with graph nodes and edges, no line geometries.

Run from simple_oficios/ (isolated mode):
    python -I tools/rnc_build.py <path/to/rnc2025.gpkg> data/rnc/rnc_nacional.sqlite

Assumption to verify: for "Un sentido" edges, travel goes from UNION_INI to UNION_FIN.
"""
import math
import sqlite3
import struct
import sys
import time
from pathlib import Path

ENVELOPE_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
CELL_DEG = 0.1  # spatial bucket (~11 km) used to load a region without a state polygon


def cell_of(lat: float, lng: float) -> int:
    return math.floor((lat + 90) / CELL_DEG) * 10_000 + math.floor((lng + 180) / CELL_DEG)


def point_lnglat(blob: bytes) -> tuple[float, float]:
    """Decode a GeoPackage POINT blob into (lng, lat)."""
    if blob[:2] != b"GP":
        raise ValueError("not a GeoPackage geometry blob")
    flags = blob[3]
    offset = 8 + ENVELOPE_BYTES[(flags >> 1) & 7]
    endian = "<" if blob[offset] == 1 else ">"
    if struct.unpack_from(endian + "I", blob, offset + 1)[0] != 1:
        raise ValueError("not a point")
    return struct.unpack_from(endian + "dd", blob, offset + 5)


class Codes:
    """Map repeated text values to small integers, keeping the lookup for the output file."""

    def __init__(self) -> None:
        self.ids: dict[str, int] = {}

    def __call__(self, value) -> int:
        value = "" if value is None else str(value)
        return self.ids.setdefault(value, len(self.ids))


def to_int(value, default=None):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def main(src: str, dst: str) -> None:
    t0 = time.time()
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    if Path(dst).exists():
        raise SystemExit(f"{dst} already exists; remove it first")
    src_db = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    out = sqlite3.connect(dst)
    out.executescript("""
        pragma journal_mode = off; pragma synchronous = off;
        create table nodes (id integer primary key, lat real not null, lng real not null, cell integer not null);
        create table edges (id integer primary key, ini integer, fin integer, len_m real, speed_kmh integer,
                            oneway integer, closed integer, level integer, tipo integer, estatus integer,
                            condicion integer, peaje integer, jurisdi integer);
        create table codes (field text, code integer, value text);
    """)

    batch, n_nodes, n_dupes = [], 0, 0
    for fid, ident, blob in src_db.execute("select fid, id_union, geom from union_p"):
        lng, lat = point_lnglat(blob)
        batch.append((ident, lat, lng, cell_of(lat, lng)))
        if len(batch) >= 100_000:
            before = out.total_changes
            out.executemany("insert or ignore into nodes values (?,?,?,?)", batch)
            n_dupes += len(batch) - (out.total_changes - before)
            n_nodes += len(batch)
            batch = []
    if batch:
        before = out.total_changes
        out.executemany("insert or ignore into nodes values (?,?,?,?)", batch)
        n_dupes += len(batch) - (out.total_changes - before)
        n_nodes += len(batch)
    out.commit()
    print(f"nodes: {n_nodes} read, {n_dupes} duplicate ids ignored ({time.time() - t0:.0f}s)", flush=True)

    tipo, estatus, condicion, peaje, jurisdi = Codes(), Codes(), Codes(), Codes(), Codes()
    cols = ("id_red, union_ini, union_fin, longitud, velocidad, circula, nivel, "
            "tipo_vial, estatus, condicion, peaje, jurisdi")
    batch, n_edges = [], 0
    for (ident, ini, fin, length, speed, circula, nivel, t, st, cond, toll, jur) in src_db.execute(
        f"select {cols} from red_vial"
    ):
        batch.append((ident, ini, fin, length, to_int(speed), 1 if circula == "Un sentido" else 0,
                      1 if circula == "Cerrada en ambos sentidos" else 0, nivel,
                      tipo(t), estatus(st), condicion(cond), peaje(toll), jurisdi(jur)))
        if len(batch) >= 100_000:
            out.executemany("insert into edges values (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            n_edges += len(batch)
            batch = []
    if batch:
        out.executemany("insert into edges values (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        n_edges += len(batch)
    for field, codes in (("tipo", tipo), ("estatus", estatus), ("condicion", condicion),
                         ("peaje", peaje), ("jurisdi", jurisdi)):
        out.executemany("insert into codes values (?,?,?)", [(field, c, v) for v, c in codes.ids.items()])
    out.commit()
    print(f"edges: {n_edges} ({time.time() - t0:.0f}s)", flush=True)

    out.executescript("""
        create index nodes_cell on nodes (cell);
        create index edges_ini on edges (ini);
        create index edges_fin on edges (fin);
    """)
    out.commit()
    print(f"indexes built ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
