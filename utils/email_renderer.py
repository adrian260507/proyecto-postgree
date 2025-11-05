from flask import render_template
from flask_mail import Message
from flask import current_app
import os

def get_email_css():
    """
    Lee el archivo CSS de emails y lo devuelve como string
    """
    try:
        css_path = os.path.join(current_app.root_path, 'static', 'css', 'email_styles.css')
        current_app.logger.info(f"📁 Buscando CSS en: {css_path}")
        
        if not os.path.exists(css_path):
            current_app.logger.error(f"❌ Archivo CSS no encontrado: {css_path}")
            return "/* CSS no encontrado */"
            
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            current_app.logger.info(f"✅ CSS cargado correctamente, tamaño: {len(css_content)} caracteres")
            return css_content
    except Exception as e:
        current_app.logger.error(f"❌ Error leyendo CSS de emails: {str(e)}")
        return "/* Error cargando CSS */"

def render_email(template_path, **context):
    """
    Renderiza una plantilla de correo electrónico
    """
    try:
        current_app.logger.info(f"🎨 Renderizando plantilla: {template_path}")
        
        # Contexto común para todos los correos
        base_context = {
            'base_url': current_app.config.get('BASE_URL', 'http://localhost:5000'),
            'app_name': 'Connexa - Sistema de Gestión',
            'support_email': 'asistenciasgtc@gmail.com'
        }
        base_context.update(context)
        
        # Renderizar el template
        current_app.logger.info(f"📝 Contexto para plantilla: {list(base_context.keys())}")
        html_content = render_template(template_path, **base_context)
        current_app.logger.info(f"✅ Plantilla renderizada, tamaño: {len(html_content)} caracteres")
        
        # Inyectar CSS inline en el HTML
        css_content = get_email_css()
        html_with_css = html_content.replace('</head>', f'<style>{css_content}</style></head>')
        
        if '</head>' not in html_content:
            current_app.logger.warning("⚠️ No se encontró </head> en la plantilla, CSS no se inyectó")
            html_with_css = f"<style>{css_content}</style>{html_content}"
        
        return html_with_css
        
    except Exception as e:
        current_app.logger.error(f"❌ Error renderizando plantilla {template_path}: {str(e)}")
        raise

def send_templated_email(subject, recipients, template_path, **context):
    """
    Envía un correo usando una plantilla
    """
    try:
        current_app.logger.info(f"📤 Intentando enviar correo a: {recipients}")
        current_app.logger.info(f"📧 Asunto: {subject}")
        current_app.logger.info(f"📄 Plantilla: {template_path}")
        
        # Verificar configuración de email
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        
        if not mail_username or not mail_password:
            current_app.logger.error("❌ Credenciales de email no configuradas")
            return False
            
        # Renderizar HTML con CSS inline
        html_body = render_email(template_path, **context)
        
        # Generar versión texto plano
        text_body = generate_plain_text(html_body)
        
        msg = Message(
            subject=subject,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            recipients=recipients
        )
        msg.body = text_body
        msg.html = html_body
        
        mail = current_app.extensions['mail']
        mail.send(msg)
        
        current_app.logger.info(f"✅ Correo enviado exitosamente a {recipients}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Error enviando correo con plantilla {template_path}: {str(e)}")
        current_app.logger.error(f"🔧 Detalles del error: {type(e).__name__}")
        return False

def generate_plain_text(html_content):
    """
    Genera una versión en texto plano del HTML
    """
    import re
    try:
        # Eliminar etiquetas HTML
        text = re.sub(r'<[^>]+>', '', html_content)
        # Reemplazar entidades HTML
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        # Colapsar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        current_app.logger.error(f"❌ Error generando texto plano: {str(e)}")
        return "Error generando contenido de texto plano"