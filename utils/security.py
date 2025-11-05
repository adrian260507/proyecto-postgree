from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required as flask_login_required

# Mantenemos el decorator login_required de Flask-Login
login_required = flask_login_required
#funcion para crear el decorador del rol requerido
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.rol_id not in roles:
                flash("No tienes permisos para acceder a esta página.", "danger")
                return redirect(url_for("publico.inicio_publico"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator