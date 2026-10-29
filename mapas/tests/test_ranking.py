"""Checks of the mechanic ranking: E preference, Bayesian score, gates and phased search."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import ranking as rk  # noqa: E402
from tools.ranking import Candidato  # noqa: E402


def cand(id, dist=1, rating=4.5, n=100, declara=False, trabajos=0):
    return Candidato(id, f"Taller {id}", dist, rating, n, declara, trabajos)


def test_niveles_e():
    assert rk.nivel_e(cand("a")) == 0
    assert rk.nivel_e(cand("a", declara=True)) == 1
    assert rk.nivel_e(cand("a", trabajos=1)) == 2
    assert rk.nivel_e(cand("a", trabajos=4)) == 2
    assert rk.nivel_e(cand("a", trabajos=5)) == 3


def test_preferencia_E3_sobre_E2_sobre_E1_sobre_E0_aunque_sea_peor_en_lo_demas():
    lejos_y_peor = dict(rating=4.0, n=20)
    pool = [cand("e0", 1, rating=4.9, n=5000),
            cand("e1", 2, declara=True, rating=4.8, n=2000),
            cand("e2", 3, trabajos=1, rating=4.5, n=500),
            cand("e3", 9, trabajos=7, **lejos_y_peor)]
    orden = [r["id"] for r in rk.ranking_mecanicos(pool)]
    assert orden == ["e3", "e2", "e1", "e0"]


def test_score_bayesiano_del_ejemplo():
    a = rk.score_bayesiano(5.0, 1)
    b = rk.score_bayesiano(4.5, 10_000)
    c = rk.score_bayesiano(4.8, 20)
    assert a == pytest.approx(4.2157, abs=1e-3)
    assert b == pytest.approx(4.4985, abs=1e-3)
    assert c == pytest.approx(4.3714, abs=1e-3)
    assert b > c > a


def test_empate_en_E_decide_el_score_y_luego_la_distancia():
    pool = [cand("cerca_peor", 1, rating=4.2, n=100, declara=True),
            cand("lejos_mejor", 8, rating=4.8, n=100, declara=True),
            cand("empate_cerca", 2, rating=4.8, n=100, declara=True)]
    assert [r["id"] for r in rk.ranking_mecanicos(pool)] == ["empate_cerca", "lejos_mejor", "cerca_peor"]


def test_puertas_excluyen():
    pool = [cand("poco_rating", 1, rating=3.5), cand("pocas_resenas", 1, n=5), cand("ok", 5)]
    assert [r["id"] for r in rk.ranking_mecanicos(pool)] == ["ok"]


def test_flujo_2_ignora_la_experiencia():
    pool = [cand("sin_exp_mejor", 1, rating=4.9, n=1000), cand("con_exp", 1, rating=4.1, n=100, trabajos=9)]
    assert rk.ranking_mecanicos(pool, con_experiencia=False)[0]["id"] == "sin_exp_mejor"
    assert rk.ranking_mecanicos(pool)[0]["id"] == "con_exp"


def test_fases_se_amplian_hasta_encontrar_especialista():
    pool = [cand(f"n{i}", i + 1) for i in range(30)]             # nearest 30: nobody specialises
    pool += [cand(f"m{i}", 40 + i) for i in range(35)]           # 31st..65th: none either
    pool.append(cand("especialista", 90, declara=True))          # 66th nearest: phase 3 (up to 100)
    r = rk.buscar_por_fases(pool)
    assert r["encontrado"] and r["fase"] == 3
    assert r["resultados"][0]["id"] == "especialista"


def test_sin_especialista_ofrece_los_mejores_cercanos():
    pool = [cand("a", 1, rating=4.3), cand("b", 2, rating=4.9, n=800)]
    r = rk.buscar_por_fases(pool)
    assert not r["encontrado"]
    assert r["resultados"][0]["id"] == "b"
