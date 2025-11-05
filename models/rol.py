from .db import q_exec

def ensure_roles():
    # id_rol: 1 Usuario, 2 Administrador, 3 Organizador
    for rid, name in [(1, "Usuario"), (2, "Administrador"), (3, "Organizador")]:
        q_exec(
            "INSERT INTO roles (id_rol, nombre) VALUES (%s,%s) "
            "ON CONFLICT (id_rol) DO UPDATE SET nombre=EXCLUDED.nombre",
            (rid, name)
        )