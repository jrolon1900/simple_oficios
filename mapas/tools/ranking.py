"""Ranking of registered mechanics: lexicographic key (experience level E, rating score, distance).

Preference over experience levels:  E=3  ≻  E=2  ≻  E=1  ≻  E=0
  E=0  no evidence
  E=1  declares the required specialty
  E=2  at least 1 verified job in that specialty with satisfaction >= 4
  E=3  at least 5 such jobs

Rating score is the Bayesian average  (n / (n + m)) * R + (m / (n + m)) * C,  so a 5-star shop with a
single review does not beat a 4.5-star shop with thousands.

The defaults for m, C and the quality gates come from a Google-reviews world; with our own
reviews at launch almost every shop has a small n, so lower them (for example m=5, min_resenas=3).
"""
from dataclasses import dataclass

NIVELES_E = (0, 1, 2, 3)  # higher is preferred
FASES = (30, 60, 100)     # nearest candidates considered in phases 1, 2 and 3

PRIOR_M = 50
PRIOR_C = 4.2
MIN_RATING = 4.0
MIN_RESENAS = 20


@dataclass(frozen=True)
class Candidato:
    id: str
    nombre: str
    distancia: float                  # km in a straight line, or minutes by road: lower is closer
    rating: float | None = None       # 0 to 5
    n_resenas: int = 0
    declara_especialidad: bool = False
    trabajos_verificados: int = 0     # verified jobs in the requested specialty, satisfaction >= 4


def nivel_e(c: Candidato) -> int:
    if c.trabajos_verificados >= 5:
        return 3
    if c.trabajos_verificados >= 1:
        return 2
    if c.declara_especialidad:
        return 1
    return 0


def score_bayesiano(rating: float | None, n: int, m: float = PRIOR_M, c: float = PRIOR_C) -> float:
    if not rating or n <= 0:
        return c
    return (n / (n + m)) * rating + (m / (n + m)) * c


def pasa_puertas(cand: Candidato, min_rating: float, min_resenas: int) -> bool:
    return (cand.rating or 0) >= min_rating and cand.n_resenas >= min_resenas


def clave(cand: Candidato, m: float, c: float, con_experiencia: bool = True) -> tuple:
    """Sort key, ascending = better: compared left to right, each part only breaks ties of the previous."""
    e = nivel_e(cand) if con_experiencia else 0
    return (-e, -score_bayesiano(cand.rating, cand.n_resenas, m, c), cand.distancia)


def _ficha(cand: Candidato, m: float, c: float) -> dict:
    return {"id": cand.id, "nombre": cand.nombre, "nivel_e": nivel_e(cand),
            "score": round(score_bayesiano(cand.rating, cand.n_resenas, m, c), 3),
            "distancia": cand.distancia}


def ranking_mecanicos(candidatos, *, con_experiencia: bool = True, m: float = PRIOR_M,
                      c: float = PRIOR_C, min_rating: float = MIN_RATING,
                      min_resenas: int = MIN_RESENAS, limite: int = 5) -> list[dict]:
    """Rank candidates that pass the quality gates. Flow 2 (top 5 nearest) uses con_experiencia=False."""
    aptos = [x for x in candidatos if pasa_puertas(x, min_rating, min_resenas)]
    aptos.sort(key=lambda x: clave(x, m, c, con_experiencia))
    return [_ficha(x, m, c) for x in aptos[:limite]]


def buscar_por_fases(candidatos, *, fases=FASES, m: float = PRIOR_M, c: float = PRIOR_C,
                     min_rating: float = MIN_RATING, min_resenas: int = MIN_RESENAS,
                     limite: int = 5) -> dict:
    """Phased search over candidates sorted by closeness (30, then 60, then 100 nearest).

    A phase succeeds when some shop in it passes the gates AND has E >= 1. If no phase succeeds,
    the answer says nobody works on this problem and offers the best-rated nearby shops instead.
    """
    cercanos = sorted(candidatos, key=lambda x: x.distancia)
    for numero, k in enumerate(fases, start=1):
        pool = cercanos[:k]
        if any(pasa_puertas(x, min_rating, min_resenas) and nivel_e(x) >= 1 for x in pool):
            return {"encontrado": True, "fase": numero,
                    "resultados": ranking_mecanicos(pool, m=m, c=c, min_rating=min_rating,
                                                    min_resenas=min_resenas, limite=limite)}
    pool = cercanos[:fases[-1]]
    return {"encontrado": False, "fase": len(fases),
            "resultados": ranking_mecanicos(pool, con_experiencia=False, m=m, c=c, min_rating=min_rating,
                                            min_resenas=min_resenas, limite=limite)}
