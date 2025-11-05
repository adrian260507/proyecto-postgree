#!/usr/bin/env bash
# build.sh - Script de construcción para Render

echo "Instalando dependencias..."
pip install -r requirements.txt

# Crear tablas en la base de datos si es necesario
python -c "
import sys
sys.path.append('.')
from app import create_app
from models import crear_tablas
from models.rol import ensure_roles
from models.user import ensure_default_admin

app = create_app()
with app.app_context():
    try:
        crear_tablas()
        ensure_roles()
        ensure_default_admin()
        print('✅ Base de datos inicializada correctamente')
    except Exception as e:
        print(f'⚠️ Advertencia durante inicialización: {e}')
"