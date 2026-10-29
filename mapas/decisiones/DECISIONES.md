# Decisiones de Simple Oficios

Generadas con el modelo lexicográfico de `lexicografico.py`. Para recalcular:
`python decisiones/lexicografico.py`.

## Orden de criterios (fijado por el equipo)

C1 Flujo núcleo > C3 Riesgo bajo > C2 Confianza > C4 Poco esfuerzo > C5 Bajo costo > C6 Diferenciación

El método no compensa: una ventaja en un criterio alto vale más que cualquier ventaja en los de abajo.
Los puntajes (1 a 3) son juicios del equipo, no mediciones.

## Premisas

- Piloto en CDMX; el filtro por estado aplica a talleres y mecánicos.
- Los leads para mecánicos son gratuitos (sin pasarela de pagos).
- La base de datos (Supabase) y sus pruebas son de Jorge; aquí solo van los agentes y el despliegue.
- Despliegue en Vercel. Límites verificados en su documentación: paquete Python de 500 MB, 300 s en
  Hobby, 2 GB de memoria; Hobby es solo para uso personal no comercial.
- Datos abiertos de INEGI: DENUE (talleres) y Red Nacional de Caminos (calles).

## Resultados

| Decisión | Gana | Robustez* |
|---|---|---|
| D1 Fuente de talleres | DENUE + mecánicos registrados | 75 % |
| D2 Reputación y experiencia | Reseñas propias verificadas (nivel E + promedio bayesiano) | 75 % |
| D3 Prelista por cercanía | Los k más cercanos: 30, luego 60, luego 100 | 67 % |
| D4 Ranking final | Lexicográfico con puertas y promedio bayesiano | 50 % |
| D5 Agenda | Aprobación del mecánico, sin pago | 75 % |
| D10 Cercanía real | Grafo de la RNC en 2 etapas (Haversine y luego tiempo por calles) | 47 % |
| D11 LLM en producción | Proveedor de pago (**pendiente**: el equipo tiene claves; falta saber de qué proveedor) | 50 % |
| D12 Arquitectura | Todo en Vercel: Next.js + FastAPI/Strands como funciones Python | 100 % |
| D13 Datos geográficos | SQLite embebida en la función (DENUE y RNC de CDMX) | 67 % |

\* Porcentaje de los 720 órdenes posibles de criterios en los que la opción gana.

## Regla de preferencia de experiencia (E)

E=3 ≻ E=2 ≻ E=1 ≻ E=0. Clave de orden: (−E, −score bayesiano, distancia). Ver `tools/ranking.py`.

## Pendientes

- Proveedor de las claves de API y sus términos para uso en producción (D11).
- Dueño de la cuenta de Vercel y plan (Hobby o Pro).
- Valores de `m`, `C` y de las puertas de calidad para reseñas propias al arrancar.
- Verificar el sentido de circulación de la RNC antes de rutear.
- Campo de estado en la tabla de mecánicos (base de Jorge).
- Tiempo disponible y reglas del reto.
