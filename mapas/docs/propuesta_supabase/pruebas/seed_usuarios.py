"""Create (or refresh) the test users, profiles and mechanic shops. Idempotent.

Run from simple_oficios/: python pruebas/seed_usuarios.py
"""
import supa


def asegurar_auth(admin: "supa.Client", u: dict) -> str:
    password = supa._env("PRUEBAS_PASSWORD")
    # user_metadata in case the project has a signup trigger that fills profiles from it
    meta = {"full_name": u["full_name"], "role": u["role"]}
    try:
        r = admin.auth.admin.create_user(
            {"email": u["email"], "password": password, "email_confirm": True, "user_metadata": meta}
        )
        return r.user.id
    except Exception:
        for existing in admin.auth.admin.list_users():
            if existing.email == u["email"]:
                admin.auth.admin.update_user_by_id(existing.id, {"password": password})
                return existing.id
        raise


def main() -> None:
    admin = supa.admin()
    for clave, u in supa.USUARIOS.items():
        uid = asegurar_auth(admin, u)
        admin.table("profiles").upsert(
            {"id": uid, "full_name": u["full_name"], "role": u["role"], "phone": u["phone"]}
        ).execute()
        if u["role"] == "mechanic":
            admin.table("mechanic_profiles").upsert(
                {"user_id": uid, **u["shop"], "verified": True, "active": True}
            ).execute()
        print(f"ok  {clave:10} {u['email']}")


if __name__ == "__main__":
    main()
