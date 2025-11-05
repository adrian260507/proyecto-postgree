# utils/filters.py
from datetime import datetime

#Funcion que Convierte una fecha a formato largo en español
def fecha_larga(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z","").replace(" ", "T"))
        except Exception:
            return dt
    meses = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    return f"{dt.day} de {meses[dt.month-1]} de {dt.year}"

#Funcion que permite que la fecha sea actualizada
def fecha_actualizada(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z","").replace(" ", "T"))
        except Exception:
            return dt
    return dt.strftime("%Y-%m-%d %H:%M")

def es_pasado(fecha):
    """Verifica si una fecha es pasada"""
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace('Z', '').replace(' ', 'T'))
        except:
            return False
    return fecha < datetime.now()

def imagen_evento(tipo_evento):
    """Devuelve la imagen correspondiente al tipo de evento"""
    from controllers.publico_controller import IMG_EVENTOS
    from flask import current_app
    
    if not tipo_evento:
        current_app.logger.warning("❌ tipo_evento es None o vacío")
        return IMG_EVENTOS.get("foro")
    
    tipo = str(tipo_evento).lower().strip()
    
    if tipo in IMG_EVENTOS:
        return IMG_EVENTOS[tipo]
    else:
        current_app.logger.warning(f"❌ Tipo '{tipo}' no encontrado. Usando imagen por defecto")
        return IMG_EVENTOS.get("foro")

def format_time(value, default=''):
    """Convierte timedelta o time a string HH:MM"""
    if value is None:
        return default
    
    try:
        # Si es timedelta
        if hasattr(value, 'seconds'):
            total_seconds = value.seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        
        # Si es time
        elif hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        
        # Si ya es string
        elif isinstance(value, str):
            return value
            
        return default
    except Exception:
        return default
#funcion que registra filtros personalizados para las plantillas del aplicativo

def register_filters(app):
    app.add_template_filter(fecha_larga, name="fecha_larga")
    app.add_template_filter(fecha_actualizada, name="fecha_actualizada")
    app.add_template_filter(imagen_evento, name="imagen_evento")
    app.add_template_filter(es_pasado, name="es_pasado")
    app.add_template_filter(format_time, name="format_time") 