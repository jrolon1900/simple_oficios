# pruebas

Pruebas del modelo de datos en Supabase con dos clientes y tres mecánicos ficticios de CDMX.
El esquema se monta sobre las tablas que ya existen en el proyecto (`profiles`, `mechanic_profiles`,
`appointments`); `supabase/schema.sql` solo agrega columnas, una tabla y dos funciones.

1. En Supabase, abre **SQL Editor**, pega todo `supabase/schema.sql` y ejecuta.
2. En **Project Settings → API** copia la URL, la clave `anon` (o publishable) y la `service_role` (o secret).
3. Agrégalas al `.env` (ver `.env.example`) junto con una contraseña de pruebas en `PRUEBAS_PASSWORD`.
4. Desde `simple_oficios/`:

```bash
python pruebas/seed_usuarios.py
python -m pytest pruebas -v
```

Qué verifican:
- Búsqueda con puertas de calidad y ranking bayesiano (`search_mechanics`).
- El teléfono de un mecánico no es visible para un cliente.
- Solo las partes de una cita la ven; solo el mecánico asignado la aprueba (`respond_appointment`).
- Cada lado firma su propio reporte post-cita (doble confirmación).

La clave `service_role` salta las reglas de seguridad: solo para el seed y la limpieza, nunca en un frontend ni en git.

Supuestos a confirmar con Jorge: `profiles.role` usa `client` / `mechanic`, y `appointments.status` usa
`pending` / `approved` / `rejected` / `cancelled` / `completed` / `no_show`.
