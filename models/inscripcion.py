from .db import q_all, q_one, q_exec
from flask import current_app

#funcion para verificar si el usuario esta inscrito 
def esta_inscrito(eid: int, uid: int):
    return q_one(
        "SELECT id_inscripcion FROM inscripciones WHERE id_evento=%s AND id_usuario=%s AND activo=1",
        (eid, uid)
    )
    
#funcion para obtener el cupo ocupado de un evento 
def cupo_ocupado(eid: int) -> int:
    r = q_one("SELECT COUNT(*) c FROM inscripciones WHERE id_evento=%s AND activo=1", (eid,), dictcur=True)
    return r["c"] if r else 0

#funcion para inscibirse en un evento 
def inscribir(eid: int, uid: int):
    return q_exec("INSERT INTO inscripciones (id_usuario, id_evento, activo) VALUES (%s,%s,1)", (uid, eid))

# models/inscripcion.py
def mis_eventos(uid: int):
    """Obtener todos los eventos del usuario (incluyendo pasados)"""
    eventos = q_all("""
        SELECT i.id_inscripcion, e.id_evento, e.nombre, e.tipo_evento, 
               e.fecha_inicio, e.fecha_fin, i.asistio, i.porcentaje_asistencia
        FROM inscripciones i
        INNER JOIN eventos e ON i.id_evento = e.id_evento
        WHERE i.id_usuario = %s AND i.activo=1 AND e.activo=1
        ORDER BY e.fecha_inicio DESC
    """, (uid,), dictcur=True)
    
    # Calcular porcentajes para eventos que no lo tengan
    for evento in eventos:
        if evento.get('porcentaje_asistencia') is None:
            porcentaje = calcular_porcentaje_asistencia(
                evento['id_inscripcion'], 
                evento['id_evento'], 
                uid
            )
            evento['porcentaje_asistencia'] = porcentaje
    
    return eventos

#funcion para desincribirse de los eventos
def desinscribir(insc_id: int):
    q_exec("UPDATE inscripciones SET activo=0, updated_at=CURRENT_TIMESTAMP WHERE id_inscripcion=%s", (insc_id,))

def calcular_porcentaje_asistencia(insc_id: int, eid: int, uid: int):
    """Calcula el porcentaje de asistencia para una inscripción - VERSIÓN MEJORADA"""
    try:
        from datetime import date
        
        # Obtener información del evento
        evento = q_one("""
            SELECT fecha_inicio, fecha_fin, hora_inicio_diaria, hora_fin_diaria 
            FROM eventos 
            WHERE id_evento=%s
        """, (eid,), dictcur=True)
        
        if not evento:
            return 0
        
        # Calcular días totales del evento
        fecha_inicio = evento['fecha_inicio'].date() if hasattr(evento['fecha_inicio'], 'date') else evento['fecha_inicio']
        fecha_fin = evento['fecha_fin'].date() if hasattr(evento['fecha_fin'], 'date') else evento['fecha_fin']
        
        # Asegurar que son fechas válidas
        if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
            current_app.logger.error(f"❌ Fechas inválidas para evento {eid}")
            return 0
        
        dias_totales = (fecha_fin - fecha_inicio).days + 1
        
        if dias_totales <= 0:
            current_app.logger.warning(f"⚠️ Evento {eid} tiene días totales <= 0: {dias_totales}")
            return 0

        # Contar días con asistencia confirmada
        asistencias = q_one("""
            SELECT COUNT(DISTINCT fecha) as total 
            FROM asistencias 
            WHERE id_evento=%s AND id_usuario=%s AND asistio=1 AND activo=1
        """, (eid, uid), dictcur=True)
        
        dias_asistidos = asistencias['total'] if asistencias else 0
        
        # Calcular porcentaje
        porcentaje = (dias_asistidos / dias_totales) * 100 if dias_totales > 0 else 0
        
        current_app.logger.info(f"📊 Usuario {uid} - Asistencia: {dias_asistidos}/{dias_totales} = {porcentaje:.1f}%")
        
        return porcentaje
        
    except Exception as e:
        current_app.logger.error(f"❌ Error calculando porcentaje asistencia: {str(e)}")
        return 0

def marcar_certificado_notificado(insc_id: int):
    """Marca que se notificó al usuario sobre el certificado"""
    q_exec("UPDATE inscripciones SET certificado_notificado=1 WHERE id_inscripcion=%s", (insc_id,))

def puede_descargar_certificado(porcentaje: float) -> bool:
    """Verifica si el usuario puede descargar el certificado (80% mínimo)"""
    return porcentaje >= 80.0