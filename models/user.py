from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .db import q_one, q_exec
import random
from datetime import datetime, timedelta

class User(UserMixin):
    # ... (el resto de la clase se mantiene igual, solo cambian las consultas)
    
    @staticmethod
    def set_verification_token(user_id, token):
        q_exec(
            "UPDATE usuarios SET verification_token=%s, token_created_at=CURRENT_TIMESTAMP WHERE id_usuario=%s",
            (token, user_id)
        )

    @staticmethod
    def get_by_email(email: str):
        row = q_one("""
            SELECT u.*, ur.id_rol 
            FROM usuarios u 
            LEFT JOIN usuarios_roles ur ON u.id_usuario = ur.id_usuario 
            WHERE u.correo=%s
        """, (email,), dictcur=True)
        # ... (resto del método igual)

    @staticmethod
    def get_by_id(uid: int):
        row = q_one("""
            SELECT u.*, ur.id_rol 
            FROM usuarios u 
            LEFT JOIN usuarios_roles ur ON u.id_usuario = ur.id_usuario 
            WHERE u.id_usuario=%s
        """, (uid,), dictcur=True)
        # ... (resto del método igual)

    @staticmethod
    def create_user(nombre, apellido, correo, contrasena, celular=None, documento_id=None):
        hashed = generate_password_hash(contrasena)
        uid = q_exec("""
            INSERT INTO usuarios (nombre, apellido, correo, contrasena, celular, documento_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (nombre, apellido, correo, hashed, (celular or None), (documento_id or None)))
        
        q_exec("""
            INSERT INTO usuarios_roles (id_usuario, id_rol)
            VALUES (%s, 1)
            ON CONFLICT (id_usuario, id_rol) DO NOTHING
        """, (uid,))
        return uid

def ensure_default_admin():
    admin = q_one("""
        SELECT u.id_usuario
        FROM usuarios u
        JOIN usuarios_roles ur ON ur.id_usuario=u.id_usuario
        WHERE ur.id_rol=2
        LIMIT 1
    """)
    if admin:
        return
    uid = User.create_user("Admin", "Sistema", "admin@sgtc.local", "Admin123*")
    q_exec("UPDATE usuarios_roles SET id_rol=2 WHERE id_usuario=%s", (uid,))