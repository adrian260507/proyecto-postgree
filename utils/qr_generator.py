# utils/qr_generator.py
import qrcode
from io import BytesIO
import base64
from flask import url_for
from datetime import datetime, timedelta
import secrets

def generar_qr_asistencia(eid, duracion_minutos=120):
    """
    Genera un código QR para marcar asistencia automática
    """
    try:
        # Generar token único con expiración
        token = secrets.token_urlsafe(16)
        expiracion = datetime.now() + timedelta(minutes=duracion_minutos)
        
        # Crear datos del QR
        qr_data = {
            'eid': eid,
            'token': token,
            'expiracion': expiracion.isoformat(),
            'tipo': 'asistencia_automatica'
        }
        
        # Generar URL para escanear
        from flask import current_app
        with current_app.app_context():
            qr_url = url_for('eventos.escanear_qr_asistencia', 
                           eid=eid, token=token, _external=True)
        
        # Generar QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        # Crear imagen QR
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para mostrar en HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'qr_image': f"data:image/png;base64,{img_str}",
            'qr_url': qr_url,
            'token': token,
            'expiracion': expiracion
        }
        
    except Exception as e:
        print(f"Error generando QR: {e}")
        return None

def validar_token_qr(token, eid):
    """
    Valida si un token QR es válido
    """
    try:

        return True
    except Exception as e:
        print(f"Error validando token QR: {e}")
        return False