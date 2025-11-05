from flask import current_app
from models.evento import obtener_eventos_recientemente_terminados
from utils.mailer import enviar_certificados_masivo_evento_terminado
from models.db import q_exec

def procesar_eventos_terminados():
    """Procesa automáticamente eventos que terminaron recientemente"""
    try:
        current_app.logger.info("🔄 Iniciando procesamiento de eventos terminados...")
        
        # Obtener eventos que terminaron en los últimos 2 días
        eventos_terminados = obtener_eventos_recientemente_terminados(2)
        
        if not eventos_terminados:
            current_app.logger.info("✅ No hay eventos recientemente terminados")
            return True
        
        current_app.logger.info(f"📅 Encontrados {len(eventos_terminados)} eventos terminados")
        
        for evento in eventos_terminados:
            current_app.logger.info(f"📨 Procesando evento: {evento['nombre']}")
            enviar_certificados_masivo_evento_terminado(evento)
        
        current_app.logger.info("✅ Procesamiento de eventos terminados completado")
        return True
        
    except Exception as e:
        current_app.logger.error(f"💥 Error en procesamiento automático: {str(e)}")
        return False
#por comentar

def procesar_eventos_terminados():
    """Procesa automáticamente eventos que terminaron recientemente - SOLO NOTIFICA UNA VEZ"""
    try:
        current_app.logger.info("🔄 Iniciando procesamiento de eventos terminados...")
        
        # Obtener eventos que terminaron en los últimos 2 días
        eventos_terminados = obtener_eventos_recientemente_terminados(2)
        
        if not eventos_terminados:
            current_app.logger.info("✅ No hay eventos recientemente terminados")
            return True
        
        current_app.logger.info(f"📅 Encontrados {len(eventos_terminados)} eventos terminados")
        
        for evento in eventos_terminados:
            current_app.logger.info(f"📨 Procesando evento: {evento['nombre']}")
            
            # VERIFICAR SI YA SE PROCESÓ ESTE EVENTO
            from models.db import q_one
            ya_procesado = q_one(
                "SELECT id_evento FROM eventos_procesados WHERE id_evento=%s AND fecha_procesado >= DATE_SUB(NOW(), INTERVAL 1 DAY)",
                (evento['id_evento'],)
            )
            
            if not ya_procesado:
                enviar_certificados_masivo_evento_terminado(evento)
                # MARCAR COMO PROCESADO
                q_exec(
                    "INSERT INTO eventos_procesados (id_evento, fecha_procesado) VALUES (%s, NOW()) ON DUPLICATE KEY UPDATE fecha_procesado=NOW()",
                    (evento['id_evento'],)
                )
            else:
                current_app.logger.info(f"⏭️ Evento {evento['nombre']} ya fue procesado hoy")
        
        current_app.logger.info("✅ Procesamiento de eventos terminados completado")
        return True
        
    except Exception as e:
        current_app.logger.error(f"💥 Error en procesamiento automático: {str(e)}")
        return False