import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash
from flask import session, flash, redirect, url_for, current_app
from functools import wraps

def conectar():
    cfg = current_app.config
    return psycopg2.connect(
        host=cfg["DB_HOST"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        port=cfg["DB_PORT"]
    )

# =========================
# CREACIÓN DE TABLAS PARA POSTGRESQL
# =========================
def crear_tablas():
    con = conectar()
    cur = con.cursor()

    # Crear tipo ENUM para modalidad
    cur.execute("""
        DO $$ BEGIN
            CREATE TYPE modalidad_type AS ENUM ('virtual', 'presencial');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Tabla usuarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            apellido VARCHAR(100),
            correo VARCHAR(150) NOT NULL UNIQUE,
            contrasena VARCHAR(255) NOT NULL,
            celular VARCHAR(20),
            documento_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT true,
            email_verified BOOLEAN DEFAULT false,
            verification_token VARCHAR(10),
            token_created_at TIMESTAMP
        )
    """)

    # Tabla roles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id_rol SERIAL PRIMARY KEY,
            nombre VARCHAR(50) NOT NULL UNIQUE,
            activo BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabla usuarios_roles (muchos a muchos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_roles (
            id_usuario_rol SERIAL PRIMARY KEY,
            id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
            id_rol INTEGER REFERENCES roles(id_rol),
            UNIQUE (id_usuario, id_rol)
        )
    """)

    # Tabla eventos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id_evento SERIAL PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL,
            tipo_evento VARCHAR(50),
            fecha_inicio TIMESTAMP,
            fecha_fin TIMESTAMP,
            lugar VARCHAR(150),
            ciudad VARCHAR(100),
            descripcion TEXT,
            cupo_maximo INTEGER,
            id_organizador INTEGER REFERENCES usuarios(id_usuario),
            activo BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modalidad modalidad_type DEFAULT 'presencial',
            enlace_virtual VARCHAR(500),
            hora_inicio_diaria TIME,
            hora_fin_diaria TIME
        )
    """)

    # Tabla inscripciones
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inscripciones (
            id_inscripcion SERIAL PRIMARY KEY,
            id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
            id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
            asistio BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            certificado_notificado BOOLEAN DEFAULT false,
            porcentaje_asistencia DECIMAL(5,2) DEFAULT 0.00,
            UNIQUE (id_usuario, id_evento)
        )
    """)

    # Tabla asistencias
    cur.execute("""
        CREATE TABLE IF NOT EXISTS asistencias (
            id_asistencia SERIAL PRIMARY KEY,
            id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
            id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
            fecha DATE,
            asistio BOOLEAN DEFAULT false,
            activo BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (id_evento, id_usuario, fecha)
        )
    """)

    # Tabla certificados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS certificados (
            id_certificado SERIAL PRIMARY KEY,
            id_inscripcion INTEGER REFERENCES inscripciones(id_inscripcion) ON DELETE CASCADE,
            fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            numero_serie VARCHAR(64),
            archivo BYTEA,
            activo BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enviado_por_correo BOOLEAN DEFAULT false
        )
    """)

    # Tabla qr_asistencias
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_asistencias (
            id_qr SERIAL PRIMARY KEY,
            id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
            token VARCHAR(64) UNIQUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion TIMESTAMP,
            activo BOOLEAN DEFAULT true,
            usado_por INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.commit()
    con.close()

# =========================
# FUNCIONES DE CONSULTA (actualizadas para PostgreSQL)
# =========================
def q_all(sql, params=(), dictcur=True):
    con = conectar()
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor if dictcur else None)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    con.close()
    
    if dictcur and rows:
        return [dict(row) for row in rows]
    return rows

def q_one(sql, params=(), dictcur=True):
    rows = q_all(sql, params, dictcur=dictcur)
    return rows[0] if rows else None

def q_exec(sql, params=()):
    con = conectar()
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    
    # Para PostgreSQL, obtener el último ID insertado
    if sql.strip().upper().startswith('INSERT'):
        cur.execute("SELECT LASTVAL()")
        last_id = cur.fetchone()[0]
    else:
        last_id = None
        
    cur.close()
    con.close()
    return last_id

# =========================
# DECORADORES (se mantienen igual)
# =========================
def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            flash("Debes iniciar sesión.", "warning")
            return redirect(url_for("auth.login"))
        return f(*a, **k)
    return w

def role_required(*ids):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "uid" not in session:
                flash("Debes iniciar sesión.", "warning")
                return redirect(url_for("auth.login"))
            if session.get("rol_id") not in ids:
                flash("No tienes permisos.", "danger")
                return redirect(url_for("publico.inicio_publico"))
            return f(*a, **k)
        return w
    return deco