# Propuesta de esquema para Supabase

**Es una propuesta, no está aplicada.** La base de datos y sus pruebas son de Jorge.

- `supabase/schema.sql`: cambios aditivos sobre `profiles`, `mechanic_profiles` y `appointments`
  (columnas de búsqueda y reputación, tabla `appointment_reports`, funciones `respond_appointment`
  y `search_mechanics`). Supone `profiles.role` = `client` | `mechanic` y `appointments.status` =
  `pending` | `approved` | `rejected` | `cancelled` | `completed` | `no_show`.
- `pruebas/`: usuarios ficticios de CDMX y pruebas de las reglas de seguridad. Necesitan claves de
  Supabase en un `.env` y escriben datos en la base, así que se corren solo con acuerdo de Jorge.
