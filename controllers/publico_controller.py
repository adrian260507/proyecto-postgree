from flask import request, render_template, current_app,abort, flash, redirect, url_for
from flask_login import current_user
from . import publico_bp
from models.db import q_all
from datetime import datetime

#Diccionario con las imagenes de los eventos
IMG_EVENTOS = {
    "foro": "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1200&q=60",
    "debate": "https://images.unsplash.com/photo-1529070538774-1843cb3265df?auto=format&fit=crop&w=1200&q=60",
    "taller": "https://thumbs.dreamstime.com/b/grupo-de-j%C3%B3venes-multi%C3%A9tnicos-emprendedores-que-colaboran-en-proyectos-oficinas-modernas-%C3%A9xito-trabajando-equipo-juntos-338967711.jpg",
    "simposio": "https://medios.ut.edu.co/wp-content/uploads/2018/12/IMG_8466.jpg",
    "seminario": "https://plus.unsplash.com/premium_photo-1679547202717-c1fea70eb817?fm=jpg&q=60&w=3000&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1yZWxhdGVkfDE2fHx8ZW58MHx8fHx8",
    "conferencia": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=60",
    "panel de expertos": "https://www.educablog.es/wp-content/uploads/2024/12/como-crear-un-panel-de-expertos-para-tu-evento-en-5-sencillos-pasos-aprende-a-seleccionar-invitar-y-coordinar-a-los-mejores-profesionales-para-tu-evento.jpg",
}

#ruta de inicio publico
@publico_bp.route("/")
def inicio_publico():
    tipos = request.args.getlist("tipo")
    
    # Solo eventos activos y futuros para vista pública
    sql = """
        SELECT id_evento, nombre, tipo_evento, fecha_inicio, fecha_fin, 
               lugar, ciudad, cupo_maximo, id_organizador, modalidad, enlace_virtual 
        FROM eventos 
        WHERE activo=1 AND fecha_fin >= CURDATE()
    """
    params = []
    
    if tipos:
        placeholders = ",".join(["%s"] * len(tipos))
        sql += f" AND tipo_evento IN ({placeholders})"
        params.extend(tipos)
    
    sql += " ORDER BY fecha_inicio ASC LIMIT 12"
    
    eventos = q_all(sql, tuple(params), dictcur=True)
    
    inscritas = set()
    if current_user.is_authenticated:
        try:
            rows = q_all("SELECT id_evento FROM inscripciones WHERE id_usuario=%s AND activo=1", 
                       (current_user.id,), dictcur=True)
            for r in rows:
                inscritas.add(r["id_evento"])
        except Exception as e:
            current_app.logger.error(f"Error al obtener inscripciones: {e}")

    return render_template(
        "home/inicio.html",
        eventos=eventos,
        tipos_seleccionados=set(tipos),
        IMG_EVENTOS=IMG_EVENTOS,
        inscritas=inscritas
    )
#Ruta de quienes somos
@publico_bp.route("/quienes-somos")
def quienes_somos():
    return render_template("info/quienes_somos.html")
#Ruta de contacto
@publico_bp.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        # Recoger datos del formulario
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        asunto = request.form.get("asunto", "").strip()
        mensaje = request.form.get("mensaje", "").strip()
        
        # Validaciones básicas
        if not nombre or not email or not asunto or not mensaje:
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("info/contacto.html")
        
        if len(mensaje) < 10:
            flash("El mensaje debe tener al menos 10 caracteres.", "warning")
            return render_template("info/contacto.html")
        
        try:
            # Enviar correo de contacto
            from utils.mailer import enviar_correo_contacto
            from datetime import datetime
            
            # Obtener información adicional
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', 'No disponible')
            fecha_consulta = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Enviar correo
            exito = enviar_correo_contacto(
                nombre=nombre,
                email=email,
                telefono=telefono,
                asunto=asunto,
                mensaje=mensaje,
                ip_address=ip_address,
                user_agent=user_agent,
                fecha_consulta=fecha_consulta
            )
            
            if exito:
                flash("¡Mensaje enviado correctamente! Te contactaremos pronto.", "success")
                return redirect(url_for('publico.contacto'))
            else:
                flash("Error al enviar el mensaje. Por favor, intenta nuevamente.", "danger")
                
        except Exception as e:
            current_app.logger.error(f"Error en formulario de contacto: {str(e)}")
            flash("Ocurrió un error inesperado. Por favor, intenta más tarde.", "danger")
    
    return render_template("info/contacto.html")
