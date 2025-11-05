from datetime import date
from .db import q_all, q_one, q_exec
from flask import current_app

#funcion para obtener lista de usuarios inscritos
def listar_inscritos(eid: int):
    return q_all("""
        SELECT u.ID_usuario, 
               CONCAT(u.nombre,' ',IFNULL(u.apellido,'')) as nombre, 
               u.correo,
               (SELECT CONCAT(org.nombre,' ',IFNULL(org.apellido,'')) 
                FROM usuarios org 
                WHERE org.ID_usuario = e.id_organizador) as organizador_nombre
        FROM inscripciones i
        JOIN usuarios u ON u.ID_usuario = i.id_usuario
        JOIN eventos e ON e.id_evento = i.id_evento
        WHERE i.id_evento = %s AND i.activo = 1 AND u.activo = 1
        ORDER BY u.nombre
    """, (eid,), dictcur=True)
  #funcion que devuelve un diccionario con las asistencias del evento
  
def get_matriz(eid: int):
    rows = q_all("SELECT id_usuario, fecha, asistio FROM asistencias WHERE id_evento=%s AND activo=1", (eid,), dictcur=True)
    return {
        (r["id_usuario"], (r["fecha"].isoformat() if isinstance(r["fecha"], date) else str(r["fecha"]))): r["asistio"]
        for r in rows
    }
#funcion para guardar datos en la base de datos
def guardar(eid: int, dias, marcados_por_uid: dict):
    """Guarda las asistencias y actualiza los porcentajes"""
    try:
        # Upsert de asistencias
        for uid, fechas in marcados_por_uid.items():
            for d, asistio in fechas.items():
                row = q_one("""
                    SELECT id_asistencia FROM asistencias 
                    WHERE id_evento=%s AND id_usuario=%s AND fecha=%s
                """, (eid, uid, d))
                
                if row:
                    asid = row[0] if not isinstance(row, dict) else row.get("id_asistencia")
                    q_exec("UPDATE asistencias SET asistio=%s, updated_at=NOW() WHERE id_asistencia=%s", 
                          (1 if asistio else 0, asid))
                else:
                    q_exec("""
                        INSERT INTO asistencias (id_evento, id_usuario, fecha, asistio, activo)
                        VALUES (%s,%s,%s,%s,1)
                    """, (eid, uid, d, 1 if asistio else 0))

        # ACTUALIZACIÓN CRÍTICA: Marcar asistencia en inscripciones y calcular porcentajes
        from .inscripcion import calcular_porcentaje_asistencia
        
        # Obtener todas las inscripciones del evento
        inscripciones = q_all("""
            SELECT id_inscripcion, id_usuario 
            FROM inscripciones 
            WHERE id_evento=%s AND activo=1
        """, (eid,), dictcur=True)
        
        for insc in inscripciones:
            # Calcular porcentaje actual
            porcentaje = calcular_porcentaje_asistencia(
                insc['id_inscripcion'], 
                eid, 
                insc['id_usuario']
            )
            
            # Determinar si asistió (al menos 1 día de asistencia)
            asistio_result = q_one("""
                SELECT COUNT(*) as total 
                FROM asistencias 
                WHERE id_evento=%s AND id_usuario=%s AND asistio=1
            """, (eid, insc['id_usuario']), dictcur=True)
            
            asistio_flag = 1 if asistio_result and asistio_result['total'] > 0 else 0
            
            # Actualizar inscripción
            q_exec("""
                UPDATE inscripciones 
                SET asistio=%s, porcentaje_asistencia=%s, updated_at=NOW()
                WHERE id_inscripcion=%s
            """, (asistio_flag, porcentaje, insc['id_inscripcion']))
            
        current_app.logger.info(f"✅ Asistencias actualizadas para evento {eid}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Error guardando asistencias: {str(e)}")
        return False