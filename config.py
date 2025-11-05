import os
from dotenv import load_dotenv 
from urllib.parse import urlparse
import re

load_dotenv() 

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod-12345")
    
    # Configuración de PostgreSQL para Render
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        # Parsear la URL de la base de datos de Render
        url = urlparse(DATABASE_URL)
        DB_HOST = url.hostname
        DB_USER = url.username
        DB_PASSWORD = url.password
        DB_NAME = url.path[1:]  # Remover el slash inicial
        DB_PORT = url.port or 5432
    else:
        # Configuración local
        DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
        DB_USER = os.getenv("DB_USER", "postgres")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        DB_NAME = os.getenv("DB_NAME", "sistemagestionbd")
        DB_PORT = int(os.getenv("DB_PORT", "5432"))

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "asistenciasgtc@gmail.com")
    
    # URL base para producción
    BASE_URL = os.getenv("BASE_URL", "https://tu-app.onrender.com")
    
    MAIL_TEMPLATE_FOLDER = "mails"

    # Session
    SESSION_PROTECTION = 'strong'  
    
    # Configuración para producción
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    
    # Configuración del host y puerto para Render
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("PORT", "10000"))