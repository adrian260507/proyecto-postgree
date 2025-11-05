from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from utils.security import role_required
from models.db import q_all, q_one, q_exec

@admin_bp.route("/roles")
@role_required(2)
def admin_roles():
        # Consulta todos los usuarios con su primer rol asignado

    usuarios = q_all("""
        SELECT u.ID_usuario, u.nombre, u.apellido, u.correo, u.activo,
               (SELECT nombre FROM roles r
                JOIN usuarios_roles ur ON ur.id_rol=r.id_rol
                WHERE ur.id_usuario=u.ID_usuario LIMIT 1) AS rol
        FROM usuarios u
        ORDER BY u.nombre
    """, dictcur=True)
        # Consulta todos los roles disponibles en el sistema

    roles = q_all("SELECT id_rol, nombre FROM roles ORDER BY id_rol", dictcur=True)
    return render_template("admin/admin_roles.html", usuarios=usuarios, roles=roles)

#Asignar/actualizar roles de usuarios (Requiere admin)
@admin_bp.route("/roles/asignar", methods=["POST"])
@role_required(2)
def admin_roles_asignar():
        # Obtener datos del formulario
    uid = int(request.form["id_usuario"])
    rol_id = int(request.form["id_rol"])
    actividad = int(request.form["actividad"])
        # Verificar si el usuario ya tiene un rol asignado

    if q_one("SELECT id_usuario_rol FROM usuarios_roles WHERE id_usuario=%s", (uid,)):
         # Usuario existe: actualizar rol

        q_exec("UPDATE usuarios_roles SET id_rol=%s WHERE id_usuario=%s", (rol_id, uid))
    else:
        q_exec("INSERT INTO usuarios_roles (id_usuario, id_rol) VALUES (%s,%s)", (uid, rol_id))
    q_exec("UPDATE usuarios SET activo=%s WHERE ID_usuario=%s", (actividad, uid))
    flash("Rol actualizado.", "success")
    return redirect(url_for("admin.admin_roles"))

@admin_bp.route("/usuarios")
@role_required(2)
def admin_usuarios():
    """Gestión de usuarios con filtros avanzados"""
    # Obtener filtros
    filtros = {
        'nombre': request.args.get('nombre', ''),
        'correo': request.args.get('correo', ''),
        'rol': request.args.get('rol', ''),
        'estado': request.args.get('estado', ''),
        'page': request.args.get('page', 1, type=int)
    }
    
    # Paginación
    per_page = 15
    offset = (filtros['page'] - 1) * per_page
    
    # Construir consulta
    sql = """
        SELECT u.ID_usuario, u.nombre, u.apellido, u.correo, u.activo, u.created_at,
               r.id_rol, r.nombre as rol_nombre
        FROM usuarios u
        LEFT JOIN usuarios_roles ur ON u.ID_usuario = ur.id_usuario
        LEFT JOIN roles r ON ur.id_rol = r.id_rol
        WHERE 1=1
    """
    params = []
    
    # Aplicar filtros
    if filtros['nombre']:
        sql += " AND (u.nombre LIKE %s OR u.apellido LIKE %s)"
        params.extend([f"%{filtros['nombre']}%", f"%{filtros['nombre']}%"])
    if filtros['correo']:
        sql += " AND u.correo LIKE %s"
        params.append(f"%{filtros['correo']}%")
    if filtros['rol']:
        sql += " AND r.id_rol = %s"
        params.append(filtros['rol'])
    if filtros['estado']:
        if filtros['estado'] == 'activo':
            sql += " AND u.activo = 1"
        elif filtros['estado'] == 'inactivo':
            sql += " AND u.activo = 0"
    
    # Contar total
    count_sql = "SELECT COUNT(*) as total FROM (" + sql + ") as filtered"
    total = q_one(count_sql, tuple(params), dictcur=True)['total']
    
    # Aplicar paginación
    sql += " ORDER BY u.nombre, u.apellido LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    usuarios = q_all(sql, tuple(params), dictcur=True)
    roles = q_all("SELECT id_rol, nombre FROM roles ORDER BY id_rol", dictcur=True)
    
    return render_template("admin/admin_usuarios.html",
                         usuarios=usuarios,
                         roles=roles,
                         filtros=filtros,
                         pagination={
                             'page': filtros['page'],
                             'per_page': per_page,
                             'total': total,
                             'pages': (total + per_page - 1) // per_page
                         })
