from flask import Blueprint

publico_bp = Blueprint("publico", __name__)
auth_bp    = Blueprint("auth", __name__)
eventos_bp = Blueprint("eventos", __name__)
admin_bp   = Blueprint("admin", __name__)

# Importa para registrar las rutas en los blueprints
from . import publico_controller, auth_controller, eventos_controller, admin_controller  # noqa