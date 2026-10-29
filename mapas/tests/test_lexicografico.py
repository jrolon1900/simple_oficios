"""Checks of the lexicographic ordering logic (not of the judgments inside the scores)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from decisiones import lexicografico as lx  # noqa: E402


def test_primer_criterio_domina_todo():
    ops = {"A": (3, 1, 1, 1, 1, 1), "B": (2, 3, 3, 3, 3, 3)}
    assert lx.ganadores(ops) == ["A"]


def test_empate_pasa_al_siguiente_criterio():
    ops = {"A": (3, 2, 1, 1, 1, 1), "B": (3, 2, 2, 1, 1, 1), "C": (3, 1, 3, 3, 3, 3)}
    por_riesgo = ["C1", "C2", "C3", "C4", "C5", "C6"]  # explicit: independent of the team's default
    assert lx.ganadores(ops, por_riesgo) == ["B"]
    assert lx.ranking(ops, por_riesgo) == ["B", "A", "C"]


def test_orden_fijado_por_el_equipo():
    assert lx.ORDEN_POR_DEFECTO == ["C1", "C3", "C2", "C4", "C5", "C6"]
    ops = {"A": (3, 3, 1, 1, 1, 1), "B": (3, 2, 3, 1, 1, 1)}  # B is safer, A is more trustworthy
    assert lx.ganadores(ops) == ["B"]


def test_el_orden_de_criterios_cambia_el_resultado():
    ops = {"A": (3, 3, 1, 1, 1, 1), "B": (3, 2, 3, 1, 1, 1)}
    assert lx.ganadores(ops, ["C1", "C2", "C3", "C4", "C5", "C6"]) == ["A"]
    assert lx.ganadores(ops, ["C1", "C3", "C2", "C4", "C5", "C6"]) == ["B"]


def test_vectores_identicos_son_empate():
    ops = {"A": (2, 2, 2, 2, 2, 2), "B": (2, 2, 2, 2, 2, 2)}
    assert lx.ganadores(ops) == ["A", "B"]


def test_sensibilidad_suma_uno():
    for d in lx.DECISIONES.values():
        assert sum(lx.sensibilidad(d["opciones"]).values()) == pytest.approx(1.0)


def test_todas_las_opciones_tienen_seis_puntajes_entre_1_y_3():
    for d in lx.DECISIONES.values():
        for v in d["opciones"].values():
            assert len(v) == len(lx.CRITERIOS) and all(1 <= s <= 3 for s in v)
