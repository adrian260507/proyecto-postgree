from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from . import auth_bp
from models.user import User
from models.db import q_exec
from utils.mailer import send_mail

# Crea un serializador seguro con temporizador usando la SECRET_KEY de la aplicación - 05/10/2025
def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

@auth_bp.route("/registro", methods=["GET","POST"])
def registro():
    if request.method == "POST":
          # Obtener y limpiar datos del formulario

        nombre = request.form.get("nombre","").strip()
        apellido = request.form.get("apellido","").strip()
        correo = request.form.get("correo","").strip().lower()
        contrasena = request.form.get("contrasena","").strip()
        celular = request.form.get("celular","").strip()
        documento_id = request.form.get("documento_id","").strip()

        # Validar campos obligatorios

        if not (nombre and apellido and correo and contrasena):
            flash("Completa los campos obligatorios.", "warning")
            return render_template("auth/registro.html")
        # Verificar si el correo ya está registrado

        if User.get_by_email(correo):
            flash("Ese correo ya existe.", "danger")
            return render_template("auth/registro.html")

        # Crear usuario
        uid = User.create_user(nombre, apellido, correo, contrasena, celular or None, documento_id or None)
        
        # Generar y guardar token de verificación
        token = User.generate_verification_token()
        User.set_verification_token(uid, token)
        
        # Enviar correo de verificación
        try:
            from utils.email_renderer import send_templated_email
          # Contexto para el template del email

            context = {
                'usuario_nombre': nombre,
                'verification_token': token,
                'expira_horas': 24
            }
                   # Enviar email con template

            success = send_templated_email(
                subject="🔐 Verifica tu correo electrónico - Connexa",
                recipients=[correo],
                template_path="emails/auth/verificacion_correo.html",
                **context
            )
            
            if success:
                flash("✅ Cuenta creada. Se ha enviado un código de verificación a tu correo.", "success")
                return redirect(url_for("auth.verify_email", user_id=uid))
            else:
                flash("⚠️ Cuenta creada, pero hubo un error enviando el código de verificación. Contacta al administrador.", "warning")
                return redirect(url_for("auth.login"))
                
        except Exception as e:
            current_app.logger.error(f"Error enviando correo de verificación: {e}")
            flash("⚠️ Cuenta creada, pero hubo un error enviando el código de verificación. Contacta al administrador.", "warning")
            return redirect(url_for("auth.login"))
    
    return render_template("auth/registro.html")

@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    """Página para verificar el correo electrónico"""
    user_id = request.args.get('user_id', type=int)
    
    if not user_id:
        flash("Enlace de verificación inválido.", "danger")
        return redirect(url_for("auth.registro"))
    
    user = User.get_by_id(user_id)
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("auth.registro"))
    
    # Si ya está verificado, redirigir al login
    if User.is_email_verified(user_id):
        flash("✅ Tu correo ya está verificado. Puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        
        if not token or len(token) != 6:
            flash("❌ El código debe tener 6 dígitos.", "danger")
            return render_template("auth/verify_email.html", user=user)
        
        # Verificar token
        success, message = User.verify_email_with_token(user_id, token)
        
        if success:
            flash(f"✅ {message}", "success")
            return redirect(url_for("auth.login"))
        else:
            flash(f"❌ {message}", "danger")
            return render_template("auth/verify_email.html", user=user)
    
    return render_template("auth/verify_email.html", user=user)

#Reenviar código de verificación a usuario no verificado
@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    """Reenviar código de verificación"""
    user_id = request.form.get("user_id", type=int)
    
    if not user_id:
        flash("❌ Solicitud inválida.", "danger")
        return redirect(url_for("auth.registro"))
    
    user = User.get_by_id(user_id)
    if not user:
        flash("❌ Usuario no encontrado.", "danger")
        return redirect(url_for("auth.registro"))
    
    # Generar nuevo token
    token = User.generate_verification_token()
    User.set_verification_token(user_id, token)
    
    # Reenviar correo
    try:
        from utils.email_renderer import send_templated_email
        
        context = {
            'usuario_nombre': user.nombre,
            'verification_token': token,
            'expira_horas': 24
        }
        
        success = send_templated_email(
            subject="🔐 Nuevo código de verificación - Connexa",
            recipients=[user.correo],
            template_path="emails/auth/verificacion_correo.html",
            **context
        )
        
        if success:
            flash("✅ Se ha enviado un nuevo código de verificación a tu correo.", "success")
        else:
            flash("❌ Error al reenviar el código. Contacta al administrador.", "danger")
            
    except Exception as e:
        current_app.logger.error(f"Error reenviando verificación: {e}")
        flash("❌ Error al reenviar el código. Contacta al administrador.", "danger")
    
    return redirect(url_for("auth.verify_email", user_id=user_id))

# Ruta para inicio de sesión de usuarios
@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        flash("Ya tienes una sesión activa.", "info")
        return redirect(url_for("publico.inicio_publico"))
    
    if request.method == "POST":
        correo = request.form.get("correo","").strip().lower()
        contrasena = request.form.get("contrasena","").strip()
        user = User.get_by_email(correo)
        
        if user and check_password_hash(user.contrasena, contrasena):
            if not user.is_active:
                flash("El usuario está deshabilitado", "danger")
            else:
                # Verificar si el correo está verificado
                if not User.is_email_verified(user.id): 
                    flash("⚠️ Por favor, verifica tu correo electrónico antes de iniciar sesión.", "warning")
                    return redirect(url_for("auth.verify_email", user_id=user.id))
                
                login_user(user)
                flash("Bienvenido/a", "success")
                return redirect(url_for("publico.inicio_publico"))
        else:
            flash("Credenciales inválidas.", "danger")
    
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("publico.inicio_publico"))

#ruta para configurar la cueta del usuario
@auth_bp.route("/configuracion", methods=["GET", "POST"])
@login_required
def configuracion_usuario():
    if request.method == "POST":
        data = {
            'nombre': request.form.get('nombre'),
            'apellido': request.form.get('apellido'),
            'celular': request.form.get('celular'),
            'documento_id': request.form.get('documento_id')
        }
        
        if User.actualizar_usuario(current_user.id, data):
            flash("Tus datos se han actualizado correctamente.", "success")
            # Recargar usuario actualizado
            updated_user = User.get_by_id(current_user.id)
            login_user(updated_user)  # Actualizar la sesión
            return redirect(url_for('auth.configuracion_usuario'))
        else:
            flash("Error al actualizar los datos. Intenta nuevamente.", "danger")
    
    return render_template("auth/configuracion_usuario.html", usuario=current_user)

#ruta para cambiar la contraseña
@auth_bp.route("/configuracion/cambiar-password", methods=["POST"])
@login_required
def cambiar_password():
    from models.db import q_exec
    from werkzeug.security import generate_password_hash
    
    password_actual = request.form.get('password_actual')
    nueva_password = request.form.get('nueva_password')
    confirmar_password = request.form.get('confirmar_password')
    
    if not password_actual or not nueva_password:
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for('auth.configuracion_usuario'))
    
    if nueva_password != confirmar_password:
        flash("Las nuevas contraseñas no coinciden.", "danger")
        return redirect(url_for('auth.configuracion_usuario'))
    
    if len(nueva_password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.", "danger")
        return redirect(url_for('auth.configuracion_usuario'))
    
    # Verificar contraseña actual
    if not check_password_hash(current_user.contrasena, password_actual):
        flash("La contraseña actual es incorrecta.", "danger")
        return redirect(url_for('auth.configuracion_usuario'))
    
    # Actualizar contraseña
    hashed_password = generate_password_hash(nueva_password)
    q_exec("UPDATE usuarios SET contrasena=%s WHERE ID_usuario=%s", 
           (hashed_password, current_user.id))
    
    flash("Contraseña actualizada correctamente.", "success")
    return redirect(url_for('auth.configuracion_usuario'))



#ruta cuando se olvida la contraseñal
@auth_bp.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        user = User.get_by_email(email)
        
        if user:
            try:
                token = _serializer().dumps(email, salt="recuperar-salt")
                link = url_for("auth.reset_password", token=token, _external=True)
                
                # USAR TEMPLATE EN LUGAR DE HTML MANUAL
                from utils.email_renderer import send_templated_email
                
                context = {
                    'usuario_nombre': user.nombre,
                    'url_reset': link
                }
                
                success = send_templated_email(
                    subject="Recuperación de contraseña - Sistema de Gestión",
                    recipients=[email],
                    template_path="emails/auth/recuperar.html",
                    **context
                )
                
                if success:
                    current_app.logger.info(f"✅ Correo de recuperación enviado exitosamente a: {email}")
                    flash("Se ha enviado un enlace de recuperación a tu correo electrónico.", "success")
                else:
                    current_app.logger.error(f"❌ Fallo al enviar correo de recuperación a: {email}")
                    flash("Error al enviar el correo. Por favor, intenta más tarde.", "danger")
                    
            except Exception as e:
                current_app.logger.exception(f"💥 Error en proceso de recuperación para {email}: {e}")
                flash("Ocurrió un error inesperado. Por favor, contacta al administrador.", "danger")
        else:
            current_app.logger.warning(f"Intento de recuperación para email no registrado: {email}")
            flash("Si existe una cuenta con ese correo, se ha enviado un enlace para restablecer la contraseña.", "info")
        
        return redirect(url_for("auth.forgot"))
    
    return render_template("auth/forgot.html")

#ruta para validar token de reinicio de contraseña
@auth_bp.route("/reset/<token>", methods=["GET","POST"])
def reset_password(token):
    try:
        email = _serializer().loads(token, salt="recuperar-salt", max_age=3600)
    except SignatureExpired:
        flash("El enlace expiró. Solicita uno nuevo.", "warning")
        return redirect(url_for("auth.forgot"))
    except BadSignature:
        flash("Token inválido.", "warning")
        return redirect(url_for("auth.forgot"))


    user = User.get_by_email(email) 
    if not user:
        flash("Cuenta no encontrada.", "danger")
        return redirect(url_for("auth.registro"))

    if request.method == "POST":
        p1 = request.form.get("password","").strip()
        p2 = request.form.get("password2","").strip()
        if not p1 or p1 != p2:
            flash("Las contraseñas no coinciden.", "warning")
            return render_template("auth/reset.html", token=token)
        hashed = generate_password_hash(p1)
        q_exec("UPDATE usuarios SET contrasena=%s WHERE correo=%s", (hashed, email))
        flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset.html", token=token)

