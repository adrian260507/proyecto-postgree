-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TIPO ENUM para modalidad
--
CREATE TYPE modalidad_type AS ENUM ('virtual', 'presencial');

--
-- Tabla: roles
--
CREATE TABLE roles (
    id_rol SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

--
-- Tabla: usuarios
--
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena VARCHAR(255) NOT NULL,
    celular VARCHAR(20),
    documento_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    verification_token VARCHAR(10),
    token_created_at TIMESTAMP
);

--
-- Tabla: usuarios_roles
--
CREATE TABLE usuarios_roles (
    id_usuario_rol SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_rol INTEGER NOT NULL REFERENCES roles(id_rol),
    UNIQUE (id_usuario, id_rol)
);

--
-- Tabla: eventos
--
CREATE TABLE eventos (
    id_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    tipo_evento VARCHAR(50) NOT NULL,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    lugar VARCHAR(150),
    ciudad VARCHAR(100),
    descripcion TEXT,
    cupo_maximo INTEGER NOT NULL,
    id_organizador INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    activo BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modalidad modalidad_type NOT NULL DEFAULT 'presencial',
    enlace_virtual VARCHAR(500),
    hora_inicio_diaria TIME,
    hora_fin_diaria TIME
);

--
-- Tabla: inscripciones
--
CREATE TABLE inscripciones (
    id_inscripcion SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_evento INTEGER NOT NULL REFERENCES eventos(id_evento) ON DELETE CASCADE,
    asistio BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    certificado_notificado BOOLEAN DEFAULT false,
    porcentaje_asistencia DECIMAL(5,2) DEFAULT 0.00,
    UNIQUE (id_usuario, id_evento)
);

--
-- Tabla: asistencias
--
CREATE TABLE asistencias (
    id_asistencia SERIAL PRIMARY KEY,
    id_evento INTEGER NOT NULL REFERENCES eventos(id_evento) ON DELETE CASCADE,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    asistio BOOLEAN NOT NULL DEFAULT false,
    activo BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_evento, id_usuario, fecha)
);

--
-- Tabla: certificados
--
CREATE TABLE certificados (
    id_certificado SERIAL PRIMARY KEY,
    id_inscripcion INTEGER NOT NULL REFERENCES inscripciones(id_inscripcion) ON DELETE CASCADE,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    numero_serie VARCHAR(64),
    archivo BYTEA,
    activo BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enviado_por_correo BOOLEAN DEFAULT false
);

--
-- Tabla: qr_asistencias
--
CREATE TABLE qr_asistencias (
    id_qr SERIAL PRIMARY KEY,
    id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP,
    activo BOOLEAN DEFAULT true,
    usado_por INTEGER DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

--
-- Datos iniciales
--
INSERT INTO roles (id_rol, nombre, activo) VALUES
(1, 'Usuario', true),
(2, 'Administrador', true),
(3, 'Organizador', true);

INSERT INTO usuarios (id_usuario, nombre, apellido, correo, contrasena, activo, email_verified) VALUES
(2, 'admin', 'admin', 'asistenciasgtc@gmail.com', 'scrypt:32768:8:1$8O4eb9z32zTcacPb$760ac834253b6c19a0a720dcbbf4ff0815de7d36c058067e2871d9347efea3640c9dd4c04bc5e5575a169fbb3f967899507dfc7bbc0b0c7ff422dcb2c8241969', true, true);

INSERT INTO usuarios_roles (id_usuario_rol, id_usuario, id_rol) VALUES
(1, 2, 2);

--
-- Índices
--
CREATE INDEX idx_asist_evt ON asistencias (id_evento);
CREATE INDEX idx_asist_user ON asistencias (id_usuario);
CREATE INDEX idx_cert_insc ON certificados (id_inscripcion);
CREATE INDEX idx_evt_org ON eventos (id_organizador);
CREATE INDEX idx_insc_evt ON inscripciones (id_evento);
CREATE INDEX idx_ur_rol ON usuarios_roles (id_rol);

--
-- Secuencias (para mantener la compatibilidad con los IDs insertados manualmente)
--
SELECT setval('roles_id_rol_seq', 3, true);
SELECT setval('usuarios_id_usuario_seq', 2, true);
SELECT setval('usuarios_roles_id_usuario_rol_seq', 1, true);