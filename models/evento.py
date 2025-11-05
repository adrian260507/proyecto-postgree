from .db import q_all, q_one, q_exec
from datetime import datetime
#por comentar

def convertir_timedelta_a_time(ev):
    """Convierte campos timedelta a time en un diccionario de evento"""
    if ev and ev.get('hora_inicio_diaria'):
        if hasattr(ev['hora_inicio_diaria'], 'seconds'):
            from datetime import time
            total_seconds = ev['hora_inicio_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_inicio_diaria'] = time(hour=hours, minute=minutes)
    
    if ev and ev.get('hora_fin_diaria'):
        if hasattr(ev['hora_fin_diaria'], 'seconds'):
            from datetime import time
            total_seconds = ev['hora_fin_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_fin_diaria'] = time(hour=hours, minute=minutes)
    
    return ev
#por comentar

def obtener_eventos_recientemente_terminados(dias=1):
    """Obtiene eventos que terminaron en los últimos X días"""
    return q_all("""
        SELECT * FROM eventos 
        WHERE fecha_fin BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND CURDATE()
        AND activo = 1
    """, (dias,), dictcur=True)
#por comentar

def listar(rol_id: int, uid: int, incluir_inactivos=False, incluir_pasados=False):
    condiciones = []
    params = []
    
    if not incluir_inactivos:
        condiciones.append("activo=true")
    
    if not incluir_pasados:
        condiciones.append("fecha_fin >= CURRENT_DATE")
    
    if rol_id == 3:
        condiciones.append("id_organizador=%s")
        params.append(uid)
    
    where_clause = " WHERE " + " AND ".join(condiciones) if condiciones else ""
    sql = f"SELECT * FROM eventos {where_clause} ORDER BY fecha_inicio ASC"
    
    eventos = q_all(sql, tuple(params), dictcur=True)
    return [convertir_timedelta_a_time(ev) for ev in eventos]

def listar_todos_para_admin(incluir_inactivos=False):
    """Listar todos los eventos para admin (incluye pasados)"""
    where_condition = "WHERE activo=1" if not incluir_inactivos else ""
    sql = f"SELECT * FROM eventos {where_condition} ORDER BY fecha_inicio DESC"
    eventos = q_all(sql, dictcur=True)
    return [convertir_timedelta_a_time(ev) for ev in eventos]
#por comentar

def obtener(eid: int):
    ev = q_one("SELECT * FROM eventos WHERE id_evento=%s AND activo=1", (eid,), dictcur=True)
    return convertir_timedelta_a_time(ev) if ev else None

#por comentar
def obtener_con_inactivos(eid: int):
    ev = q_one("SELECT * FROM eventos WHERE id_evento=%s", (eid,), dictcur=True)
    return convertir_timedelta_a_time(ev) if ev else None

#funcion para crear eventos 
def crear(data: dict, organizador_id: int):
    return q_exec("""
        INSERT INTO eventos (nombre, tipo_evento, fecha_inicio, fecha_fin, lugar, ciudad,
                             descripcion, cupo_maximo, id_organizador, modalidad, enlace_virtual,
                             hora_inicio_diaria, hora_fin_diaria)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["nombre"], data["tipo_evento"], data["fecha_inicio"], data["fecha_fin"],
        data["lugar"], data["ciudad"], data.get("descripcion",""), data["cupo_maximo"], 
        organizador_id, data["modalidad"], data.get("enlace_virtual", ""),
        data["hora_inicio_diaria"], data["hora_fin_diaria"]
    ))
        
#funcion para editar eventos
def editar(eid: int, data: dict):
    q_exec("""
        UPDATE eventos SET nombre=%s, tipo_evento=%s, fecha_inicio=%s, fecha_fin=%s,
               lugar=%s, ciudad=%s, cupo_maximo=%s, descripcion=%s, 
               modalidad=%s, enlace_virtual=%s, hora_inicio_diaria=%s, hora_fin_diaria=%s,
               updated_at=CURRENT_TIMESTAMP
        WHERE id_evento=%s
    """, (
        data["nombre"], data["tipo_evento"], data["fecha_inicio"], data["fecha_fin"],
        data["lugar"], data["ciudad"], data["cupo_maximo"], data.get("descripcion",""),
        data["modalidad"], data.get("enlace_virtual", ""),
        data["hora_inicio_diaria"], data["hora_fin_diaria"], eid
    ))
    
# funcion para desctivar eventos
def desactivar(eid: int):
    q_exec("UPDATE eventos SET activo=0, updated_at=CURRENT_TIMESTAMP WHERE id_evento=%s", (eid,))
    
#funcion para activar eventos
def activar(eid: int):
    q_exec("UPDATE eventos SET activo=1, updated_at=CURRENT_TIMESTAMP WHERE id_evento=%s", (eid,))
    
 #funcion para determinar organizador del evento 
def obtener_organizador_evento(eid: int):
    """Obtiene los datos del organizador de un evento"""
    return q_one("""
        SELECT u.ID_usuario, u.nombre, u.apellido 
        FROM eventos e
        JOIN usuarios u ON u.ID_usuario = e.id_organizador
        WHERE e.id_evento = %s
    """, (eid,), dictcur=True)