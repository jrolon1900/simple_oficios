"""Download INEGI's DENUE bulk file for one or all states and load the car-repair rows (SCIAN 8111).

    python tools/denue_bulk.py --estado 05          # Coahuila (code, name or 'cdmx')
    python tools/denue_bulk.py --estado todos       # all 32 states, one at a time

Each state is downloaded to a temporary folder, loaded and deleted before the next one: the CSV
inside is about six times the size of the zip, so keeping them all would fill the disk.
INEGI only serves the file when the request carries the download page as referer.
"""
import argparse
import csv
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import denue_load  # noqa: E402
from tools.estados import ESTADOS, resolver_estado  # noqa: E402

URL = "https://www.inegi.org.mx/contenidos/masiva/denue/denue_{parte}_csv.zip"
REFERER = "https://www.inegi.org.mx/app/descarga/?ti=6"
# INEGI publishes the Estado de México in two files; every other state is one file named after its code.
PARTES = {"15": ["15_1", "15_2"]}


def archivos_de(cve: str) -> list[str]:
    return PARTES.get(cve, [cve])


def descargar(cve: str, destino: Path, parte: str | None = None) -> Path:
    """Stream one file of a state to disk. Raises if the server answers with a page instead of a zip."""
    parte = parte or cve
    ruta = destino / f"denue_{parte}_csv.zip"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": REFERER}
    with requests.get(URL.format(parte=parte), headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(ruta, "wb") as f:
            for trozo in r.iter_content(chunk_size=1 << 20):
                f.write(trozo)
    if not zipfile.is_zipfile(ruta):
        raise RuntimeError(f"INEGI no entregó un zip para el estado {cve} (¿bloqueo o cambio de URL?)")
    return ruta


def extraer_csv(ruta_zip: Path, destino: Path) -> Path:
    """Copy the data CSV out of the zip. Reads the member as a stream; never trusts its path."""
    with zipfile.ZipFile(ruta_zip) as z:
        miembros = [m for m in z.namelist() if m.startswith("conjunto_de_datos/") and m.lower().endswith(".csv")]
        if len(miembros) != 1:
            raise RuntimeError(f"se esperaba un CSV en conjunto_de_datos/, hay {len(miembros)}")
        salida = destino / "datos.csv"
        with z.open(miembros[0]) as origen, open(salida, "wb") as f:
            shutil.copyfileobj(origen, f)
    return salida


def cargar_estado(db: sqlite3.Connection, cve: str) -> int:
    total = 0
    for parte in archivos_de(cve):
        with tempfile.TemporaryDirectory(prefix=f"denue_{parte}_") as tmp:
            tmp = Path(tmp)
            csv_path = extraer_csv(descargar(cve, tmp, parte), tmp)
            total += denue_load.load_csv(db, str(csv_path))
    return total


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--estado", required=True, help="código, nombre, 'cdmx' o 'todos'")
    args = p.parse_args(argv)
    claves = list(ESTADOS) if args.estado.lower() == "todos" else [resolver_estado(args.estado)]

    denue_load.DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(denue_load.DB)
    db.executescript(denue_load.SCHEMA)
    db.executemany("insert or replace into estados values (?,?)", list(ESTADOS.items()))
    fallos = []
    for cve in claves:
        try:
            print(f"{cve} {ESTADOS[cve]}: {cargar_estado(db, cve)} talleres", flush=True)
        except (requests.RequestException, RuntimeError, zipfile.BadZipFile, csv.Error) as e:
            fallos.append(cve)
            print(f"{cve} {ESTADOS[cve]}: FALLÓ ({type(e).__name__}: {e})", flush=True)
    db.close()
    if fallos:
        raise SystemExit(f"Estados con error: {', '.join(fallos)}")


if __name__ == "__main__":
    main()
