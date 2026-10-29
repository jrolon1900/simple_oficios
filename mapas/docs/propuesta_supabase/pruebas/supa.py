"""Shared helpers for the Supabase test folder."""
import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# Fictitious CDMX users: 2 clients and 3 mechanics. Emails use the reserved .test TLD.
USUARIOS = {
    "cliente1": {"email": "cliente1@simpleoficios.test", "role": "client",
                 "full_name": "Ana Cliente", "phone": "+52 55 0000 0001"},
    "cliente2": {"email": "cliente2@simpleoficios.test", "role": "client",
                 "full_name": "Luis Cliente", "phone": "+52 55 0000 0002"},
    "mecanico1": {"email": "mecanico1@simpleoficios.test", "role": "mechanic",
                  "full_name": "Carlos Pistón", "phone": "+52 55 0000 0011",
                  "shop": {"shop_name": "Taller El Pistón", "description": "Frenos y suspensión",
                           "city": "CDMX", "specialties": ["frenos", "suspension"],
                           "lat": 19.4195, "lng": -99.1627, "rating": 4.7, "review_count": 320}},
    "mecanico2": {"email": "mecanico2@simpleoficios.test", "role": "mechanic",
                  "full_name": "Marta Voltaje", "phone": "+52 55 0000 0012",
                  "shop": {"shop_name": "Electro Auto Coyoacán", "description": "Eléctrico y motor",
                           "city": "CDMX", "specialties": ["electrico", "motor"],
                           "lat": 19.3467, "lng": -99.1617, "rating": 4.5, "review_count": 1250}},
    "mecanico3": {"email": "mecanico3@simpleoficios.test", "role": "mechanic",
                  "full_name": "Jorge Llantas", "phone": "+52 55 0000 0013",
                  "shop": {"shop_name": "Llantas Iztapalapa", "description": "Llantas y suspensión",
                           "city": "CDMX", "specialties": ["llantas", "suspension"],
                           "lat": 19.3578, "lng": -99.0575, "rating": 4.1, "review_count": 85}},
}


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta {name} en el .env")
    return value


def admin() -> Client:
    """Service-role client: bypasses RLS. Only for seeding and cleanup."""
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def sesion(clave: str) -> tuple[Client, str]:
    """Client signed in as one of the test users, plus that user's id. Respects RLS."""
    c = create_client(_env("SUPABASE_URL"), _env("SUPABASE_ANON_KEY"))
    res = c.auth.sign_in_with_password(
        {"email": USUARIOS[clave]["email"], "password": _env("PRUEBAS_PASSWORD")}
    )
    c.postgrest.auth(res.session.access_token)
    return c, res.user.id
