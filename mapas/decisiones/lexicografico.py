"""Lexicographic decision model for Simple Oficios.

Each option gets a score vector, 1 to 3 per criterion (3 is best). Options are compared on the
first criterion of the chosen order; only if they tie does the next criterion count. The scores
are team judgments, not measurements: edit DECISIONES and re-run.

    python decisiones/lexicografico.py                       # team order C1,C3,C2,C4,C5,C6
    python decisiones/lexicografico.py --orden C1,C2,C3,C4,C5,C6
    python decisiones/lexicografico.py --decision D10
"""
import argparse
import itertools

CRITERIOS = {
    "C1": "Cubre el flujo núcleo (problema → recomendación → cita)",
    "C2": "Confianza de la recomendación",
    "C3": "Riesgo bajo (legal, privacidad, términos de uso, dinero)",
    "C4": "Poco esfuerzo de implementación",
    "C5": "Bajo costo operativo",
    "C6": "Diferenciación y explicabilidad",
}
# Fixed by the team: the core flow first, then risk, then trust, effort, cost and differentiation.
ORDEN_POR_DEFECTO = ["C1", "C3", "C2", "C4", "C5", "C6"]

# Scores follow CRITERIOS order: (C1, C2, C3, C4, C5, C6).
DECISIONES = {
    "D1": {
        "titulo": "Fuente de talleres",
        "nota": "Sin reseñas externas (opción B) la confianza descansa en verificar al mecánico.",
        "opciones": {
            "A. Google Places en vivo": (2, 2, 1, 2, 1, 2),
            "B. DENUE + mecánicos registrados": (3, 2, 3, 2, 3, 3),
            "C. Híbrido: B + reseñas de Google": (3, 3, 1, 1, 1, 3),
        },
    },
    "D2": {
        "titulo": "Reputación y experiencia con el problema",
        "nota": "Reseñas simuladas presentadas como reales serían engañosas: pierden en C2.",
        "opciones": {
            "A. Reseñas de Google": (2, 2, 1, 2, 1, 2),
            "B. Reseñas propias verificadas (nivel E + bayesiano)": (3, 2, 3, 2, 3, 3),
            "C. Reseñas simuladas para el demo": (3, 1, 2, 3, 3, 1),
        },
    },
    "D3": {
        "titulo": "Prelista por cercanía",
        "nota": "Con base propia ya no existe el tope de 20 resultados de Google.",
        "opciones": {
            "A. Los k más cercanos: 30, luego 60, luego 100": (3, 3, 3, 2, 3, 2),
            "B. Radios fijos (3, 6 y 12 km)": (3, 2, 3, 3, 3, 1),
        },
    },
    "D4": {
        "titulo": "Ranking final",
        "nota": "Un factor constante sobre la distancia no cambia el orden, solo el número mostrado.",
        "opciones": {
            "A. Lexicográfico estricto": (3, 1, 3, 3, 3, 2),
            "B. Lexicográfico con puertas y promedio bayesiano": (3, 3, 3, 2, 3, 2),
            "C. Puntaje ponderado único": (3, 3, 3, 2, 3, 1),
        },
    },
    "D5": {
        "titulo": "Agenda con el mecánico (leads gratis)",
        "nota": "Sin pago, la aprobación del mecánico es el filtro de seriedad que queda.",
        "opciones": {
            "A. Aprobación del mecánico, sin pago": (3, 3, 3, 3, 3, 2),
            "B. Cita directa, sin aprobación": (2, 2, 3, 3, 3, 1),
            "C. Aprobación + depósito del cliente": (3, 3, 1, 1, 2, 3),
        },
    },
    "D10": {
        "titulo": "Cercanía real: distancia o tiempo de viaje",
        "nota": ("RNC embebida solo cabe para CDMX; nacional pide otro servicio. La RNC no trae "
                 "tráfico; el sentido de circulación aún no está verificado."),
        "opciones": {
            "A. Línea recta (Haversine)": (3, 1, 3, 3, 3, 1),
            "B. Grafo de la RNC en 2 etapas (Haversine y luego tiempo por calles)": (3, 2, 3, 2, 3, 3),
            "C. OSRM/Valhalla autoalojado (OpenStreetMap)": (3, 2, 3, 1, 2, 2),
            "D. API con tráfico (Google/Mapbox) para los 5 finalistas": (3, 3, 1, 2, 2, 2),
        },
    },
    "D11": {
        "titulo": "LLM en producción",
        "nota": ("Premisa por confirmar: si el reto exige modelos NVIDIA, la opción B es obligatoria. "
                 "FreeLLMAPI usa un proceso persistente con SQLite local y su README lo limita a "
                 "experimentación personal."),
        "opciones": {
            "A. FreeLLMAPI desplegado en un servidor propio": (2, 2, 1, 1, 3, 1),
            "B. API de NVIDIA directa": (3, 2, 2, 3, 2, 2),
            "C. Proveedor de pago": (3, 2, 3, 3, 1, 2),
        },
    },
    "D12": {
        "titulo": "Arquitectura de despliegue",
        "nota": ("Vercel Hobby es solo para uso personal no comercial; un marketplace real pide Pro. "
                 "Python en Vercel: límite de 500 MB y 300 s por función (documentación de Vercel)."),
        "opciones": {
            "A. Todo en Vercel: Next.js + FastAPI/Strands como funciones Python": (3, 3, 2, 3, 3, 2),
            "B. Frontend en Vercel y agentes en un servicio persistente": (3, 3, 2, 2, 2, 2),
        },
    },
    "D13": {
        "titulo": "Datos geográficos en producción",
        "nota": "Embebido sirve para CDMX; al pasar a nacional hay que migrar a Postgres o a otro servicio.",
        "opciones": {
            "A. SQLite embebida en la función (DENUE y RNC de CDMX)": (3, 2, 3, 3, 3, 1),
            "B. Todo en la base de Supabase de Jorge": (3, 2, 2, 2, 3, 2),
            "C. Archivo en almacenamiento (Blob) descargado al arrancar": (3, 2, 3, 2, 2, 1),
        },
    },
}


def clave(scores, orden):
    """Sort key: scores re-ordered by priority, so Python's tuple comparison is lexicographic."""
    return tuple(scores[CRITERIOS_INDEX[c]] for c in orden)


CRITERIOS_INDEX = {c: i for i, c in enumerate(CRITERIOS)}


def ganadores(opciones, orden=None):
    """Names of the best option(s) under an order; several only when the vectors are identical."""
    orden = orden or ORDEN_POR_DEFECTO
    mejor = max(clave(v, orden) for v in opciones.values())
    return [n for n, v in opciones.items() if clave(v, orden) == mejor]


def ranking(opciones, orden=None):
    orden = orden or ORDEN_POR_DEFECTO
    return sorted(opciones, key=lambda n: clave(opciones[n], orden), reverse=True)


def sensibilidad(opciones):
    """Share of the 720 possible criteria orders in which each option wins (ties split)."""
    credito = {n: 0.0 for n in opciones}
    ordenes = list(itertools.permutations(CRITERIOS))
    for orden in ordenes:
        g = ganadores(opciones, list(orden))
        for n in g:
            credito[n] += 1 / len(g)
    return {n: c / len(ordenes) for n, c in credito.items()}


def imprimir(id_, d, orden):
    print(f"\n{id_} · {d['titulo']}")
    sens = sensibilidad(d["opciones"])
    gan = ganadores(d["opciones"], orden)
    for n in ranking(d["opciones"], orden):
        marca = "→" if n in gan else " "
        print(f" {marca} {n:<70} {d['opciones'][n]}  gana en {sens[n]:.0%} de los órdenes")
    if d.get("nota"):
        print(f"   nota: {d['nota']}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--orden", default=",".join(ORDEN_POR_DEFECTO))
    p.add_argument("--decision")
    args = p.parse_args(argv)
    orden = args.orden.split(",")
    if sorted(orden) != sorted(CRITERIOS):
        raise SystemExit(f"--orden debe contener exactamente {','.join(CRITERIOS)}")
    print("Orden de criterios: " + " > ".join(orden))
    for id_, d in DECISIONES.items():
        if not args.decision or args.decision == id_:
            imprimir(id_, d, orden)


if __name__ == "__main__":
    main()
