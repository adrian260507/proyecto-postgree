# utils/mailer.py
from flask_mail import Message
from flask import current_app, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Importamos el renderizador de emails
from .email_renderer import send_templated_email

def send_mail(subject, recipients, body, html_body=None):
    """
    Función de bajo nivel para enviar correos. 
    Preferiblemente usar send_templated_email.
    """
    try:
        msg = Message(
            subject=subject,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER", current_app.config.get("MAIL_USERNAME")),
            recipients=recipients
        )
        msg.body = body
        if html_body:
            msg.html = html_body
        
        mail = current_app.extensions['mail']
        mail.send(msg)
        current_app.logger.info(f"Correo enviado exitosamente a {recipients}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error enviando correo: {str(e)}")
        # Fallback: intentar enviar directamente con SMTP
        return _send_direct_smtp(subject, recipients, body, html_body)

def _send_direct_smtp(subject, recipients, body, html_body=None):
    """Fallback directo por SMTP si Flask-Mail falla"""
    try:
        # Configuración
        smtp_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        smtp_port = current_app.config.get("MAIL_PORT", 587)
        username = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        
        if not username or not password:
            current_app.logger.error("Credenciales de email no configuradas")
            return False
        
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        
        # Adjuntar partes
        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        
        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
        
        # Enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        current_app.logger.info(f"Correo enviado por SMTP directo a {recipients}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error en SMTP directo: {str(e)}")
        return False

# =============================================
# FUNCIONES DE CORREO CON TEMPLATES
# =============================================

def enviar_correo_contacto(nombre, email, telefono, asunto, mensaje, ip_address, user_agent, fecha_consulta):
    """
    Envía un correo con los datos del formulario de contacto
    """
    try:
        admin_email = current_app.config.get("MAIL_USERNAME")
        if not admin_email:
            current_app.logger.error("MAIL_USERNAME no configurado para correos de contacto")
            return False

        # Contexto para el template de admin
        context_admin = {
            'nombre': nombre,
            'email': email,
            'telefono': telefono or 'No proporcionado',
            'asunto': asunto,
            'mensaje': mensaje,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'fecha_consulta': fecha_consulta
        }

        # Enviar correo al admin usando template
        success_admin = send_templated_email(
            subject=f"📧 Contacto Web: {asunto}",
            recipients=[admin_email],
            template_path="emails/contacto/admin.html",
            **context_admin
        )

        if success_admin:
            # Enviar confirmación al usuario
            context_usuario = {
                'nombre': nombre,
                'asunto': asunto
            }
            success_user = send_templated_email(
                subject="✅ Confirmación de recepción - Sistema Connexa",
                recipients=[email],
                template_path="emails/contacto/usuario.html",
                **context_usuario
            )
            
            if success_user:
                current_app.logger.info(f"✅ Confirmación enviada a {email}")
            else:
                current_app.logger.error(f"❌ Error enviando confirmación a {email}")

        return success_admin
        
    except Exception as e:
        current_app.logger.error(f"💥 Error en enviar_correo_contacto: {str(e)}")
        return False

def enviar_notificacion_certificado_disponible(usuario, evento, inscripcion, porcentaje):
    """
    Envía notificación de que el certificado está disponible para descargar
    """
    try:
        context = {
            'usuario_nombre': usuario.nombre,
            'evento_nombre': evento['nombre'],
            'evento_tipo': evento['tipo_evento'],
            'fecha_inicio': evento['fecha_inicio'].strftime('%d/%m/%Y'),
            'fecha_fin': evento['fecha_fin'].strftime('%d/%m/%Y'),
            'porcentaje_asistencia': "%.1f" % porcentaje,
            'url_descarga': url_for('eventos.evento_detalle', eid=evento['id_evento'], _external=True)
        }

        success = send_templated_email(
            subject=f"🎓 Certificado disponible - {evento['nombre']}",
            recipients=[usuario.correo],
            template_path="emails/certificacion/disponible.html",
            **context
        )

        if success:
            current_app.logger.info(f"✅ Notificación de certificado enviada a {usuario.correo}")
            # Marcar como notificado en la base de datos
            from models.inscripcion import marcar_certificado_notificado
            marcar_certificado_notificado(inscripcion['id_inscripcion'])
        else:
            current_app.logger.error(f"❌ Error enviando notificación de certificado a {usuario.correo}")

        return success

    except Exception as e:
        current_app.logger.error(f"💥 Error en enviar_notificacion_certificado_disponible: {str(e)}")
        return False

def enviar_certificado_por_correo(usuario, evento, certificado_pdf, inscripcion):
    """
    Envía el certificado PDF por correo electrónico - VERSIÓN CORREGIDA
    """
    try:
        current_app.logger.info(f"📤 Enviando certificado por correo a {usuario.correo}")
        
        # DEBUG: Log para ver la estructura del objeto evento
        current_app.logger.info(f"🔍 Estructura del objeto evento: {list(evento.keys()) if isinstance(evento, dict) else 'No es dict'}")
        
        # Obtener el nombre del evento de manera segura
        evento_nombre = evento.get('nombre') or evento.get('evento') or 'Evento'
        evento_tipo = evento.get('tipo_evento') or 'Evento'
        
        # Obtener fechas de manera segura
        fecha_inicio = evento.get('fecha_inicio')
        fecha_fin = evento.get('fecha_fin')
        
        if hasattr(fecha_inicio, 'strftime'):
            fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
        else:
            fecha_inicio_str = str(fecha_inicio).split()[0] if fecha_inicio else 'Fecha no disponible'
            
        if hasattr(fecha_fin, 'strftime'):
            fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        else:
            fecha_fin_str = str(fecha_fin).split()[0] if fecha_fin else 'Fecha no disponible'

        # Crear HTML del correo
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f9f9f9;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .content {{
                    padding: 30px;
                }}
                .footer {{
                    background: #333;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                }}
                .info-box {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    border-left: 4px solid #28a745;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📜 Tu Certificado</h1>
                    <p>Sistema de Gestión de Talleres y Conferencias</p>
                </div>
                <div class="content">
                    <h2>¡Felicidades {usuario.nombre}!</h2>
                    <p>Adjunto encontrarás tu certificado de participación en el evento <strong>"{evento_nombre}"</strong>.</p>
                    
                    <div class="info-box">
                        <h3>📋 Detalles del Evento</h3>
                        <p><strong>Evento:</strong> {evento_nombre}</p>
                        <p><strong>Tipo:</strong> {evento_tipo}</p>
                        <p><strong>Fechas:</strong> {fecha_inicio_str} - {fecha_fin_str}</p>
                    </div>
                    
                    <p>Guarda este certificado en un lugar seguro, ya que es un reconocimiento a tu participación y aprendizaje.</p>
                    <p>¡Felicidades!</p>
                </div>
                <div class="footer">
                    <p>Atentamente,<br><strong>Equipo de Connexa</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        # Versión texto plano
        text_body = f"""
        Hola {usuario.nombre},

        Adjunto encontrarás tu certificado de participación en el evento "{evento_nombre}".

        Detalles:
        - Evento: {evento_nombre}
        - Tipo: {evento_tipo}
        - Fechas: {fecha_inicio_str} - {fecha_fin_str}

        Guarda este certificado en un lugar seguro, ya que es un reconocimiento a tu participación y aprendizaje.

        ¡Felicidades!

        Atentamente,
        Equipo de Connexa
        Sistema de Gestión de Talleres y Conferencias
        """

        # Enviar correo con adjunto
        msg = Message(
            subject=f"📜 Tu certificado - {evento_nombre}",
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            recipients=[usuario.correo]
        )
        msg.body = text_body
        msg.html = html_body
        
        # Adjuntar el certificado PDF
        msg.attach(
            filename=f"certificado_{evento_nombre.replace(' ', '_')}.pdf",
            content_type="application/pdf",
            data=certificado_pdf.getvalue()
        )
        
        mail = current_app.extensions['mail']
        mail.send(msg)
        
        # Marcar como enviado en la base de datos
        try:
            from models.db import q_exec
            q_exec("UPDATE certificados SET enviado_por_correo=1 WHERE id_inscripcion=%s", 
                   (inscripcion['id_inscripcion'],))
        except Exception as db_error:
            current_app.logger.warning(f"⚠️ No se pudo marcar certificado como enviado: {db_error}")
        
        current_app.logger.info(f"✅ Certificado enviado por correo a {usuario.correo}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"💥 Error en enviar_certificado_por_correo: {str(e)}")
        return False

def enviar_notificacion_no_certificacion(usuario, evento, porcentaje):
    """
    Envía notificación a usuarios que NO alcanzaron el 80% de asistencia
    """
    try:
        context = {
            'usuario_nombre': usuario.nombre,
            'evento_nombre': evento['nombre'],
            'evento_tipo': evento['tipo_evento'],
            'fecha_inicio': evento['fecha_inicio'].strftime('%d/%m/%Y'),
            'fecha_fin': evento['fecha_fin'].strftime('%d/%m/%Y'),
            'porcentaje_asistencia': "%.1f" % porcentaje,
            'mensaje_razon': obtener_mensaje_no_certificacion(porcentaje)
        }

        return send_templated_email(
            subject=f"❌ Certificado no disponible - {evento['nombre']}",
            recipients=[usuario.correo],
            template_path="emails/certificacion/no_certificacion.html",
            **context
        )

    except Exception as e:
        current_app.logger.error(f"Error enviando notificación de no certificación: {str(e)}")
        return False

def enviar_confirmacion_inscripcion(usuario, evento):
    """
    Envía confirmación de inscripción a evento
    """
    try:
        context = {
            'usuario_nombre': usuario.nombre,
            'evento_nombre': evento['nombre'],
            'evento_tipo': evento['tipo_evento'],
            'fecha_inicio': evento['fecha_inicio'].strftime('%d/%m/%Y'),
            'fecha_fin': evento['fecha_fin'].strftime('%d/%m/%Y'),
            'modalidad': evento['modalidad'],
            'enlace_virtual': evento.get('enlace_virtual', ''),
            'lugar': evento.get('lugar', ''),
            'ciudad': evento.get('ciudad', ''),
            'hora_inicio': evento.get('hora_inicio_diaria', '09:00'),
            'hora_fin': evento.get('hora_fin_diaria', '17:00')
        }

        return send_templated_email(
            subject=f"✅ Confirmación de inscripción - {evento['nombre']}",
            recipients=[usuario.correo],
            template_path="emails/eventos/confirmacion_inscripcion.html",
            **context
        )

    except Exception as e:
        current_app.logger.error(f"Error enviando confirmación de inscripción: {str(e)}")
        return False

def enviar_recuperacion_contrasena(usuario, token):
    """
    Envía correo de recuperación de contraseña
    """
    try:
        url_reset = url_for("auth.reset_password", token=token, _external=True)
        
        context = {
            'usuario_nombre': usuario.nombre,
            'url_reset': url_reset
        }

        return send_templated_email(
            subject="🔒 Recuperación de contraseña - Sistema Connexa",
            recipients=[usuario.correo],
            template_path="emails/auth/recuperar.html",
            **context
        )

    except Exception as e:
        current_app.logger.error(f"Error enviando recuperación de contraseña: {str(e)}")
        return False

# =============================================
# FUNCIONES AUXILIARES
# =============================================

def obtener_mensaje_no_certificacion(porcentaje):
    """Devuelve un mensaje personalizado según el porcentaje"""
    if porcentaje == 0:
        return "No se registró asistencia en ninguna sesión del evento."
    elif porcentaje < 50:
        return "Tu nivel de asistencia fue muy bajo para considerar la certificación."
    elif porcentaje < 80:
        return f"Te faltó un {80 - porcentaje:.1f}% de asistencia para alcanzar el mínimo requerido."
    else:
        return "Aunque tienes la asistencia requerida, hay otros criterios pendientes."

def enviar_certificados_masivo_evento_terminado(evento):
    """
    Envía certificados automáticamente a todos los que cumplieron el 80% de asistencia
    y notifica a los que no cumplieron
    """
    try:
        from models.db import q_all
        from models.inscripcion import calcular_porcentaje_asistencia, puede_descargar_certificado
        from models.user import User
        from datetime import datetime
        
        current_app.logger.info(f"🔍 Iniciando envío masivo para evento: {evento['nombre']}")
        
        # Obtener todos los inscritos en el evento
        inscritos = q_all("""
            SELECT i.id_inscripcion, i.id_usuario, i.asistio, i.porcentaje_asistencia, i.certificado_notificado,
                   u.nombre, u.apellido, u.correo, u.documento_id
            FROM inscripciones i
            JOIN usuarios u ON i.id_usuario = u.ID_usuario
            WHERE i.id_evento = %s AND i.activo = 1
        """, (evento['id_evento'],), dictcur=True)
        
        if not inscritos:
            current_app.logger.warning(f"⚠️ No hay inscritos para el evento {evento['nombre']}")
            return False
        
        certificados_enviados = 0
        notificaciones_fallidas = 0
        errores = 0
        
        for insc in inscritos:
            try:
                # Calcular porcentaje actual
                porcentaje = calcular_porcentaje_asistencia(
                    insc['id_inscripcion'], 
                    evento['id_evento'], 
                    insc['id_usuario']
                )
                
                # Crear objeto usuario
                usuario = User(
                    id_usuario=insc['id_usuario'],
                    nombre=insc['nombre'],
                    apellido=insc.get('apellido', ''),
                    correo=insc['correo'],
                    contrasena='',
                    celular=None,
                    documento_id=insc.get('documento_id'),
                    created_at=None,
                    activo=1,
                    rol_id=1
                )
                
                # Verificar si cumple los requisitos para certificado
                if puede_descargar_certificado(porcentaje) and insc['asistio']:
                    # Generar y enviar certificado
                    if enviar_certificado_individual(usuario, evento, insc):
                        certificados_enviados += 1
                        current_app.logger.info(f"✅ Certificado enviado a {usuario.correo}")
                    else:
                        errores += 1
                        current_app.logger.error(f"❌ Error enviando certificado a {usuario.correo}")
                
                else:
                    # Enviar notificación de NO certificación
                    if enviar_notificacion_no_certificacion(usuario, evento, porcentaje):
                        notificaciones_fallidas += 1
                        current_app.logger.info(f"📧 Notificación de no certificación enviada a {usuario.correo}")
                    else:
                        errores += 1
                        current_app.logger.error(f"❌ Error enviando notificación a {usuario.correo}")
                        
            except Exception as e:
                errores += 1
                current_app.logger.error(f"💥 Error procesando usuario {insc.get('correo', 'Unknown')}: {str(e)}")
        
        current_app.logger.info(f"📊 Resumen evento {evento['nombre']}: {certificados_enviados} certificados, {notificaciones_fallidas} notificaciones, {errores} errores")
        return True
        
    except Exception as e:
        current_app.logger.error(f"💥 Error crítico en envío masivo: {str(e)}")
        return False

def enviar_certificado_individual(usuario, evento, inscripcion):
    """Envía un certificado individual a un usuario"""
    try:
        # Importar desde el nuevo módulo
        from .pdf_generator import generar_pdf_certificado
        
        # Generar el PDF del certificado
        pdf_buffer = generar_pdf_certificado(usuario, evento, inscripcion)
        
        if pdf_buffer:
            return enviar_certificado_por_correo(usuario, evento, pdf_buffer, inscripcion)
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error generando certificado individual: {str(e)}")
        return False