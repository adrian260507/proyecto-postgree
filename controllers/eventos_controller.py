from datetime import datetime, timedelta, date
from io import BytesIO
from flask import render_template, request, redirect, url_for, flash, abort, current_app, send_file,jsonify    
from flask_login import current_user, login_required
from . import eventos_bp
from utils.security import role_required
from models import evento as MEvento
from models import inscripcion as MInsc
from models.asistencia import listar_inscritos, get_matriz, guardar as guardar_asistencia
from models.db import q_all, q_one
import secrets
from datetime import datetime, timedelta
from utils.qr_generator import generar_qr_asistencia, validar_token_qr
#por comentar

def _to_date(v): return v.date() if isinstance(v, datetime) else v
def rango_dias(d1:date, d2:date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

# En la función eventos_list - para usuarios normales mostrar solo futuros
@eventos_bp.route("")
@login_required
def eventos_list():
    """Muestra eventos según el rol del usuario con filtros avanzados"""
    rol = current_user.rol_id
    uid = current_user.id
    
    # OBTENER FILTROS (excluyendo 'page' de los filtros normales)
    page = request.args.get('page', 1, type=int)
    filtros = {
        'nombre': request.args.get('nombre', ''),
        'tipo': request.args.get('tipo', ''),
        'modalidad': request.args.get('modalidad', ''),
        'estado': request.args.get('estado', ''),
        'organizador': request.args.get('organizador', ''),
        'fecha_desde': request.args.get('fecha_desde', ''),
        'fecha_hasta': request.args.get('fecha_hasta', '')
    }
    
    # PAGINACIÓN
    per_page = 10
    offset = (page - 1) * per_page

    # Para usuarios normales, mostrar solo eventos futuros
    if rol == 1:
        from controllers.publico_controller import IMG_EVENTOS
        
        # Construir consulta con filtros
        sql = """
            SELECT * FROM eventos 
            WHERE activo=1 AND fecha_fin >= CURDATE()
        """
        params = []
        
        # Aplicar filtros
        if filtros['nombre']:
            sql += " AND nombre LIKE %s"
            params.append(f"%{filtros['nombre']}%")
        if filtros['tipo']:
            sql += " AND tipo_evento = %s"
            params.append(filtros['tipo'])
        if filtros['modalidad']:
            sql += " AND modalidad = %s"
            params.append(filtros['modalidad'])
        if filtros['fecha_desde']:
            sql += " AND fecha_inicio >= %s"
            params.append(filtros['fecha_desde'])
        if filtros['fecha_hasta']:
            sql += " AND fecha_fin <= %s"
            params.append(filtros['fecha_hasta'])
        
        # Contar total para paginación
        count_sql = "SELECT COUNT(*) as total FROM (" + sql + ") as filtered"
        total = q_one(count_sql, tuple(params), dictcur=True)['total']
        
        # Aplicar paginación
        sql += " ORDER BY fecha_inicio ASC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        eventos = q_all(sql, tuple(params), dictcur=True)
        
        from models.inscripcion import mis_eventos as get_mis_eventos
        eventos_inscritos = get_mis_eventos(current_user.id)
        inscritas = set([e['id_evento'] for e in eventos_inscritos])
        
        return render_template("events/eventos_publico.html", 
                             eventos=eventos, 
                             IMG_EVENTOS=IMG_EVENTOS, 
                             inscritas=inscritas,
                             filtros=filtros,
                             pagination={
                                 'page': page,
                                 'per_page': per_page,
                                 'total': total,
                                 'pages': (total + per_page - 1) // per_page
                             })
    
    # Para admin/organizador
    if rol == 3:
        sql = "SELECT * FROM eventos WHERE id_organizador=%s"
        params = [uid]
    else:
        sql = "SELECT * FROM eventos WHERE 1=1"
        params = []
    
    # Aplicar filtros
    if filtros['nombre']:
        sql += " AND nombre LIKE %s"
        params.append(f"%{filtros['nombre']}%")
    if filtros['tipo']:
        sql += " AND tipo_evento = %s"
        params.append(filtros['tipo'])
    if filtros['modalidad']:
        sql += " AND modalidad = %s"
        params.append(filtros['modalidad'])
    if filtros['estado']:
        if filtros['estado'] == 'activo':
            sql += " AND activo = 1"
        elif filtros['estado'] == 'inactivo':
            sql += " AND activo = 0"
        elif filtros['estado'] == 'futuro':
            sql += " AND fecha_inicio > CURDATE()"
        elif filtros['estado'] == 'pasado':
            sql += " AND fecha_fin < CURDATE()"
    if filtros['organizador']:
        sql += " AND id_organizador = %s"
        params.append(filtros['organizador'])
    if filtros['fecha_desde']:
        sql += " AND fecha_inicio >= %s"
        params.append(filtros['fecha_desde'])
    if filtros['fecha_hasta']:
        sql += " AND fecha_fin <= %s"
        params.append(filtros['fecha_hasta'])
    
    # Contar total para paginación
    count_sql = "SELECT COUNT(*) as total FROM (" + sql + ") as filtered"
    total = q_one(count_sql, tuple(params), dictcur=True)['total']
    
    # Aplicar paginación
    sql += " ORDER BY fecha_inicio DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    eventos = q_all(sql, tuple(params), dictcur=True)
    
    # Obtener lista de organizadores para el filtro
    organizadores = q_all("""
        SELECT DISTINCT u.ID_usuario, u.nombre 
        FROM eventos e 
        JOIN usuarios u ON e.id_organizador = u.ID_usuario 
        WHERE u.activo = 1
        ORDER BY u.nombre
    """, dictcur=True) if rol == 2 else []
    
    return render_template("events/eventos_list.html", 
                         eventos=eventos, 
                         rol=rol,
                         now=datetime.now(),
                         filtros=filtros,
                         organizadores=organizadores,
                         pagination={
                             'page': page,
                             'per_page': per_page,
                             'total': total,
                             'pages': (total + per_page - 1) // per_page
                         })

# En la función mis_eventos - mostrar todos los eventos del usuario (incluyendo pasados)
@eventos_bp.route("/mis_eventos")
@login_required
def mis_eventos():
    """Muestra todos los eventos en los que el usuario está inscrito con filtros y paginación"""
    from models.inscripcion import mis_eventos as get_mis_eventos
    from controllers.publico_controller import IMG_EVENTOS
    from datetime import datetime
    
    # Obtener parámetros de filtro
    nombre_filtro = request.args.get('nombre', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()
    fecha_inicio_filtro = request.args.get('fecha_inicio', '').strip()
    fecha_fin_filtro = request.args.get('fecha_fin', '').strip()
    
    # Obtener parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = 6

    # Obtener todos los eventos del usuario
    todos_eventos = get_mis_eventos(current_user.id)
    
    # Aplicar filtros
    eventos_filtrados = []
    for evento in todos_eventos:
        # Filtro por nombre
        if nombre_filtro and nombre_filtro.lower() not in evento['nombre'].lower():
            continue
            
        # Filtro por tipo
        if tipo_filtro and evento['tipo_evento'] != tipo_filtro:
            continue
            
        # Filtro por fecha de inicio
        if fecha_inicio_filtro:
            try:
                fecha_filtro = datetime.strptime(fecha_inicio_filtro, '%Y-%m-%d').date()
                fecha_evento = evento['fecha_inicio'].date() if hasattr(evento['fecha_inicio'], 'date') else evento['fecha_inicio']
                if fecha_evento < fecha_filtro:
                    continue
            except ValueError:
                pass  # Si hay error en el formato de fecha, ignoramos el filtro
                
        # Filtro por fecha de fin
        if fecha_fin_filtro:
            try:
                fecha_filtro = datetime.strptime(fecha_fin_filtro, '%Y-%m-%d').date()
                fecha_evento = evento['fecha_fin'].date() if hasattr(evento['fecha_fin'], 'date') else evento['fecha_fin']
                if fecha_evento > fecha_filtro:
                    continue
            except ValueError:
                pass  # Si hay error en el formato de fecha, ignoramos el filtro
        
        eventos_filtrados.append(evento)
    
    # Ordenar eventos por fecha de inicio (más recientes primero)
    eventos_filtrados.sort(key=lambda x: x['fecha_inicio'], reverse=True)
    
    # Calcular paginación
    total_eventos = len(eventos_filtrados)
    total_pages = (total_eventos + per_page - 1) // per_page
    
    # Asegurar que la página esté en rango válido
    if page < 1:
        page = 1
    elif total_pages > 0 and page > total_pages:
        page = total_pages
    
    # Calcular índices para la página actual
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    eventos_paginados = eventos_filtrados[start_idx:end_idx]
    
    # Preparar datos para la plantilla
    filtros = {
        'nombre': nombre_filtro,
        'tipo': tipo_filtro,
        'fecha_inicio': fecha_inicio_filtro,
        'fecha_fin': fecha_fin_filtro
    }
    
    return render_template("events/mis_eventos.html", 
                         filas=eventos_paginados, 
                         IMG_EVENTOS=IMG_EVENTOS,
                         filtros=filtros,
                         pagination={
                             'page': page,
                             'per_page': per_page,
                             'total': total_eventos,
                             'pages': total_pages
                         })

#ruta crear eventos
@eventos_bp.route("/nuevo", methods=["GET","POST"])
@role_required(2,3)
def eventos_nuevo():
    if request.method == "POST":
        data = {
            "nombre": request.form["nombre"].strip(),
            "tipo_evento": request.form["tipo_evento"],
            "fecha_inicio": request.form["fecha_inicio"],
            "fecha_fin": request.form["fecha_fin"],
            "hora_inicio_diaria": request.form["hora_inicio_diaria"],  
            "hora_fin_diaria": request.form["hora_fin_diaria"],        
            "lugar": request.form["lugar"].strip(),
            "ciudad": request.form["ciudad"].strip(),
            "descripcion": request.form.get("descripcion","").strip(),
            "cupo_maximo": int(request.form["cupo_maximo"]),
            "modalidad": request.form["modalidad"],
            "enlace_virtual": request.form.get("enlace_virtual", "").strip()
        }

        # Validaciones
        if data["modalidad"] == "virtual" and not data["enlace_virtual"]:
            flash("Para eventos virtuales, el enlace es obligatorio.", "danger")
            tipos = ['foro','debate','taller','simposio','panel de expertos','seminario','conferencia']
            return render_template("events/evento_form.html", modo="nuevo", tipos=tipos)

        MEvento.crear(data, current_user.id)
        flash("Evento creado.", "success")
        return redirect(url_for("eventos.eventos_list"))
    
    tipos = ['foro','debate','taller','simposio','panel de expertos','seminario','conferencia']
    return render_template("events/evento_form.html", modo="nuevo", tipos=tipos)

#ruta editar eventos
@eventos_bp.route("/<int:eid>/editar", methods=["GET","POST"])
@role_required(2,3)
def eventos_editar(eid):
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)
    if current_user.rol_id==3 and ev["id_organizador"]!=current_user.id:
        flash("No puedes editar este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))
    
    # CONVERTIR TIMEDELTA A TIME PARA LA PLANTILLA
    if ev and ev.get('hora_inicio_diaria'):
        if hasattr(ev['hora_inicio_diaria'], 'seconds'):
            # Es un timedelta, convertirlo a time
            from datetime import time
            total_seconds = ev['hora_inicio_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_inicio_diaria'] = time(hour=hours, minute=minutes)
    
    if ev and ev.get('hora_fin_diaria'):
        if hasattr(ev['hora_fin_diaria'], 'seconds'):
            # Es un timedelta, convertirlo a time
            from datetime import time
            total_seconds = ev['hora_fin_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_fin_diaria'] = time(hour=hours, minute=minutes)
    
    if request.method == "POST":
        data = {
            "nombre": request.form["nombre"].strip(),
            "tipo_evento": request.form["tipo_evento"],
            "fecha_inicio": request.form["fecha_inicio"],
            "fecha_fin": request.form["fecha_fin"],
            "hora_inicio_diaria": request.form["hora_inicio_diaria"],  
            "hora_fin_diaria": request.form["hora_fin_diaria"],        
            "lugar": request.form["lugar"].strip(),
            "ciudad": request.form["ciudad"].strip(),
            "descripcion": request.form.get("descripcion","").strip(),
            "cupo_maximo": int(request.form["cupo_maximo"]),
            "modalidad": request.form["modalidad"],
            "enlace_virtual": request.form.get("enlace_virtual", "").strip()
        }

        if data["modalidad"] == "virtual" and not data["enlace_virtual"]:
            flash("Para eventos virtuales, el enlace es obligatorio.", "danger")
            tipos = ['foro','debate','taller','simposio','panel de expertos','seminario','conferencia']
            return render_template("events/evento_form.html", modo="editar", tipos=tipos, ev=ev)

        MEvento.editar(eid, data)
        flash("Evento actualizado.", "success")
        return redirect(url_for("eventos.eventos_list"))
    
    tipos = ['foro','debate','taller','simposio','panel de expertos','seminario','conferencia']
    return render_template("events/evento_form.html", modo="editar", tipos=tipos, ev=ev)


@eventos_bp.route("/<int:eid>/eliminar", methods=["POST"])
@role_required(2,3)
def eventos_eliminar(eid):
    ev = MEvento.obtener_con_inactivos(eid)  # Cambiar a esta función para permitir desactivar eventos inactivos
    if not ev:
        abort(404)
    if current_user.rol_id==3 and ev["id_organizador"]!=current_user.id:
        flash("No puedes eliminar este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))
    
    # En lugar de eliminar, desactivar
    MEvento.desactivar(eid)
    flash("Evento desactivado correctamente.", "info")
    return redirect(url_for("eventos.eventos_list"))

#  ruta para reactivar eventos
@eventos_bp.route("/<int:eid>/activar", methods=["POST"])
@role_required(2,3)
def eventos_activar(eid):
    ev = MEvento.obtener_con_inactivos(eid)
    if not ev:
        abort(404)
    if current_user.rol_id==3 and ev["id_organizador"]!=current_user.id:
        flash("No puedes activar este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))
    
    MEvento.activar(eid)
    flash("Evento activado correctamente.", "success")
    return redirect(url_for("eventos.eventos_list"))

#ruta para abir el html de detalles evento
@eventos_bp.route("/<int:eid>")
def evento_detalle(eid):
    from controllers.publico_controller import IMG_EVENTOS
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)

    # CONVERTIR TIMEDELTA A TIME PARA LA PLANTILLA
    if ev and ev.get('hora_inicio_diaria'):
        if hasattr(ev['hora_inicio_diaria'], 'seconds'):
            from datetime import time
            total_seconds = ev['hora_inicio_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_inicio_diaria'] = time(hour=hours, minute=minutes)
    
    if ev and ev.get('hora_fin_diaria'):
        if hasattr(ev['hora_fin_diaria'], 'seconds'):
            from datetime import time
            total_seconds = ev['hora_fin_diaria'].seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            ev['hora_fin_diaria'] = time(hour=hours, minute=minutes)

    insc = None
    if current_user.is_authenticated:
        from models.db import q_one
        insc = q_one("""
            SELECT id_inscripcion, asistio, porcentaje_asistencia
            FROM inscripciones
            WHERE id_evento=%s AND id_usuario=%s AND activo=1
        """, (eid, current_user.id), dictcur=True)
        
        # Si no tiene porcentaje calculado, calcularlo
        if insc and insc.get('porcentaje_asistencia') is None:
            from models.inscripcion import calcular_porcentaje_asistencia
            porcentaje = calcular_porcentaje_asistencia(
                insc['id_inscripcion'], 
                eid, 
                current_user.id
            )
            insc['porcentaje_asistencia'] = porcentaje
    
    img = IMG_EVENTOS.get((ev.get("tipo_evento") or "").lower(), IMG_EVENTOS["foro"])
    return render_template("events/evento_detalle.html", ev=ev, img=img, insc=insc)

#generador de pdf de asistencia
@eventos_bp.route("/<int:eid>/asistencia.pdf")
@role_required(2,3)
def asistencia_pdf(eid):
    """Genera un PDF con la lista de asistencia del evento - VERSIÓN MEJORADA"""
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)
    if current_user.rol_id==3 and ev["id_organizador"]!=current_user.id:
        flash("No puedes generar el PDF de este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))

    # Obtener datos de asistencia
    di = _to_date(ev["fecha_inicio"]); df = _to_date(ev["fecha_fin"])
    dias = list(rango_dias(di, df))
    inscritos = listar_inscritos(eid)
    asis_map = get_matriz(eid)

    try:
        from reportlab.lib.pagesizes import letter, landscape, A3
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, PageBreak
        from reportlab.lib import colors
        from io import BytesIO
        from datetime import datetime
    except ImportError:
        flash("Instala reportlab: pip install reportlab", "danger")
        return redirect(url_for("eventos.asistencia", eid=eid))

    # Crear buffer para el PDF
    buffer = BytesIO()
    
    # USAR A3 LANDSCAPE PARA MÁS ESPACIO
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A3))
    
    # Configuración de estilos
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    
    # Contenido del PDF
    elements = []
    
    # Título
    title_style = styles['Heading1']
    title_style.alignment = 1  # Centrado
    elements.append(Paragraph(f"Lista de Asistencia: {ev['nombre']}", title_style))
    elements.append(Paragraph(f"Organizador: {ev.get('organizador_nombre', 'Sistema')}", styles['Normal']))
    elements.append(Paragraph(f"Del {di} al {df} - Total de participantes: {len(inscritos)}", styles['Normal']))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    
    # Espacio
    from reportlab.platypus import Spacer
    elements.append(Spacer(1, 20))
    
    # CALCULAR SI NECESITAMOS DIVIDIR LA TABLA
    max_dias_por_tabla = 10  # Máximo de días por tabla
    if len(dias) <= max_dias_por_tabla:
        # Una sola tabla
        tablas_dias = [dias]
    else:
        # Dividir los días en múltiples tablas
        tablas_dias = []
        for i in range(0, len(dias), max_dias_por_tabla):
            tablas_dias.append(dias[i:i + max_dias_por_tabla])
    
    for tabla_num, dias_tabla in enumerate(tablas_dias):
        if tabla_num > 0:
            elements.append(PageBreak())
            
        # Preparar datos para la tabla
        data = []
        
        # Encabezados de la tabla
        header = ["#", "Participante", "Correo"] + [d.strftime("%d/%m") for d in dias_tabla] + ["Asistencia"]
        data.append(header)
        
        # Datos de los participantes
        for idx, inscrito in enumerate(inscritos, 1):
            row = [str(idx), inscrito["nombre"], inscrito["correo"]]
            
            # Asistencias por día
            asistencias_dias = 0
            for d in dias_tabla:
                key = (inscrito['ID_usuario'], d.isoformat())
                if asis_map.get(key):
                    row.append("✓")
                    asistencias_dias += 1
                else:
                    row.append("✗")
            
            # Porcentaje de asistencia para estos días
            if len(dias_tabla) > 0:
                porcentaje_tabla = (asistencias_dias / len(dias_tabla)) * 100
                row.append(f"{asistencias_dias}/{len(dias_tabla)} ({porcentaje_tabla:.1f}%)")
            else:
                row.append("0/0 (0%)")
                
            data.append(row)
        
        # Crear tabla con anchos dinámicos
        col_widths = [0.4*inch, 1.8*inch, 2.2*inch] + [0.5*inch]*len(dias_tabla) + [1.2*inch]
        
        # Ajustar tabla si hay muchos días
        if len(dias_tabla) > 7:
            for i in range(3, len(dias_tabla) + 3):
                col_widths[i] = 0.4*inch  # Reducir ancho de columnas de días
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Estilo de la tabla optimizado
        table_style = TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Datos
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),  # Nombre y correo alineados a la izquierda
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            
            # Alternar colores de fila
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            
            # Resaltar totales
            ('BACKGROUND', (-1, 1), (-1, -1), colors.HexColor("#e8f5e8")),
            ('FONTNAME', (-1, 1), (-1, -1), 'Helvetica-Bold'),
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Agregar espacio entre tablas
        if tabla_num < len(tablas_dias) - 1:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"Continúa en la siguiente página...", styles['Normal']))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"asistencia_{ev['nombre'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mimetype='application/pdf'
    )

#ruta para  inscribirme
@eventos_bp.route("/<int:eid>/inscribirme", methods=["POST"])
@role_required(1)
def inscribirme(eid):
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)

    inscritos = MInsc.cupo_ocupado(eid)
    if MInsc.esta_inscrito(eid, current_user.id):
        flash("Ya estás inscrito.", "warning")
        return redirect(url_for("eventos.eventos_list"))
    if inscritos >= ev["cupo_maximo"]:
        flash("Cupo lleno.", "danger")
        return redirect(url_for("eventos.eventos_list"))

    MInsc.inscribir(eid, current_user.id)

    # Enviar correo usando template
    try:
        from utils.email_renderer import send_templated_email
        
        context = {
            'usuario_nombre': current_user.nombre,
            'evento_nombre': ev['nombre'],
            'evento_tipo': ev['tipo_evento'],
            'fecha_inicio': ev['fecha_inicio'].strftime('%d/%m/%Y'),
            'fecha_fin': ev['fecha_fin'].strftime('%d/%m/%Y'),
            'modalidad': ev['modalidad'],
            'enlace_virtual': ev.get('enlace_virtual', ''),
            'lugar': ev.get('lugar', ''),
            'ciudad': ev.get('ciudad', '')
        }
        
        send_templated_email(
            subject=f"Confirmación de inscripción - {ev['nombre']}",
            recipients=[current_user.correo],
            template_path="emails/eventos/confirmacion_inscripcion.html",
            **context
        )
    except Exception as e:
        current_app.logger.error(f"Error enviando correo de inscripción: {e}")

    flash("Inscripción realizada. Se ha enviado un correo de confirmación.", "success")
    return redirect(url_for("eventos.eventos_list"))


@eventos_bp.route("/<int:eid>/asistencia", methods=["GET","POST"])
@role_required(2,3)
def asistencia(eid):
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)
    if current_user.rol_id==3 and ev["id_organizador"]!=current_user.id:
        flash("No puedes gestionar la asistencia de este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))

    di = _to_date(ev["fecha_inicio"]); df = _to_date(ev["fecha_fin"])
    todos_los_dias = list(rango_dias(di, df))
    
    # PAGINACIÓN POR SEMANAS
    semana_actual = request.args.get('semana', 0, type=int)
    dias_por_semana = 7  # Puedes cambiar a 30 para meses
    
    # Calcular semanas totales
    total_semanas = (len(todos_los_dias) + dias_por_semana - 1) // dias_por_semana
    if semana_actual >= total_semanas:
        semana_actual = total_semanas - 1
    if semana_actual < 0:
        semana_actual = 0
    
    # Obtener días de la semana actual
    inicio_semana = semana_actual * dias_por_semana
    fin_semana = min(inicio_semana + dias_por_semana, len(todos_los_dias))  # Usamos min aquí
    dias_semana_actual = todos_los_dias[inicio_semana:fin_semana]
    
    # CALCULAR RANGOS PARA LA PLANTILLA
    primer_dia_semana = inicio_semana + 1
    ultimo_dia_semana = fin_semana  # Ya usamos min arriba
    
    # FILTRO POR FECHAS (combinado con paginación por semanas)
    fecha_inicio_filtro = request.args.get('fecha_inicio')
    fecha_fin_filtro = request.args.get('fecha_fin')
    
    if fecha_inicio_filtro and fecha_fin_filtro:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_filtro, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_filtro, '%Y-%m-%d').date()
            dias = [d for d in dias_semana_actual if fecha_inicio <= d <= fecha_fin]
        except ValueError:
            dias = dias_semana_actual
            flash("Formato de fecha inválido.", "warning")
    else:
        dias = dias_semana_actual

    if request.method == "POST":
        uids = request.form.getlist("uids")
        marcados = {}
        for uid in uids:
            uid = int(uid)
            fechas = {}
            for d in dias:
                key = f"asis[{uid}][{d.isoformat()}]"
                fechas[d] = (request.form.get(key) == "on")
            marcados[uid] = fechas
        guardar_asistencia(eid, dias, marcados)
        
        flash("Asistencia guardada.", "success")
        return redirect(url_for("eventos.asistencia", eid=eid, 
                              semana=semana_actual,
                              fecha_inicio=fecha_inicio_filtro, 
                              fecha_fin=fecha_fin_filtro))

    inscritos = listar_inscritos(eid)
    asis_map = get_matriz(eid)
    
    return render_template("events/asistencia_matriz.html", 
                         ev=ev, 
                         inscritos=inscritos, 
                         dias=dias, 
                         asis_map=asis_map,
                         fecha_inicio_filtro=fecha_inicio_filtro,
                         fecha_fin_filtro=fecha_fin_filtro,
                         total_dias=len(todos_los_dias),
                         semana_actual=semana_actual,
                         total_semanas=total_semanas,
                         dias_por_semana=dias_por_semana,
                         primer_dia_semana=primer_dia_semana,
                         ultimo_dia_semana=ultimo_dia_semana)

@eventos_bp.route("/certificado/<int:insc_id>.pdf")
@login_required
def certificado(insc_id):
    """Genera y envía certificado profesional con control de porcentaje"""
    from models.db import q_one, q_exec
    from datetime import datetime
    import os
    
    # Obtenemos datos de inscripción, evento y organizador
    row = q_one("""
        SELECT i.id_inscripcion, i.asistio, i.porcentaje_asistencia, i.certificado_notificado,
               u.ID_usuario uid, u.nombre AS usu_nombre, u.apellido AS usu_apellido, u.documento_id, u.correo,
               e.id_evento, e.nombre AS evento, e.fecha_inicio, e.fecha_fin, e.id_organizador, e.tipo_evento,
               e.fecha_fin < CURDATE() as evento_terminado
        FROM inscripciones i
        JOIN usuarios u ON u.ID_usuario = i.id_usuario
        JOIN eventos e ON e.id_evento = i.id_evento
        WHERE i.id_inscripcion = %s
    """, (insc_id,), dictcur=True)

    if not row:
        abort(404)

    # Permisos
    if current_user.id != row["uid"] and current_user.rol_id not in (2,3):
        flash("No autorizado.", "danger")
        return redirect(url_for("publico.inicio_publico"))

    # Verificar porcentaje mínimo de asistencia (80%)
    porcentaje_requerido = 80.0
    porcentaje_actual = row.get('porcentaje_asistencia', 0)
    
    # Si el porcentaje no está calculado, calcularlo ahora
    if porcentaje_actual == 0:
        from models.inscripcion import calcular_porcentaje_asistencia
        porcentaje_actual = calcular_porcentaje_asistencia(insc_id, row['id_evento'], row['uid'])
    
    if porcentaje_actual < porcentaje_requerido:
        flash(f"❌ Necesitas al menos el {porcentaje_requerido}% de asistencia para descargar el certificado. Tu porcentaje actual es: {porcentaje_actual:.1f}%", "warning")
        return redirect(url_for("eventos.evento_detalle", eid=row['id_evento']))

    if not row["asistio"]:
        flash("Certificado disponible solo para asistentes confirmados.", "warning")
        return redirect(url_for("publico.inicio_publico"))

    # OBTENER DATOS DEL ORGANIZADOR POR SEPARADO
    organizador = q_one("""
        SELECT u.nombre, u.apellido 
        FROM usuarios u 
        WHERE u.ID_usuario = %s
    """, (row['id_organizador'],), dictcur=True)

    # Nombre del participante y organizador
    nombre_participante = f"{row['usu_nombre']} {row.get('usu_apellido','')}".strip()
    
    # Determinar nombre del organizador
    if organizador:
        org_nombre = f"{organizador['nombre']} {organizador.get('apellido', '')}".strip()
    else:
        if current_user.rol_id in [2, 3]:
            org_nombre = f"{current_user.nombre} {current_user.apellido or ''}".strip()
        else:
            org_nombre = "Coordinador del Evento"
    
    if not org_nombre.strip():
        org_nombre = "Coordinador del Evento"
    
    # Generar número de certificado único
    numero_certificado = f"CERT-{insc_id}-{datetime.now().strftime('%Y%m%d')}"

    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
    except ImportError:
        flash("Error: reportlab no está instalado.", "danger")
        return redirect(url_for("publico.inicio_publico"))

    # Crear buffer para el PDF
    buf = BytesIO()
    
    # Configurar documento en formato horizontal
    doc = SimpleDocTemplate(
        buf, 
        pagesize=landscape(letter),
        leftMargin=50, 
        rightMargin=50, 
        topMargin=40, 
        bottomMargin=40
    )

    # Función para agregar borde decorativo
    def add_border(canvas, doc):
        canvas.saveState()
        # Borde exterior grueso
        canvas.setStrokeColor(colors.HexColor("#5B3E1D"))
        canvas.setLineWidth(3)
        canvas.rect(15, 15, doc.width + 70, doc.height + 70)
        
        # Borde interior fino
        canvas.setStrokeColor(colors.HexColor("#8B6914"))
        canvas.setLineWidth(1)
        canvas.rect(25, 25, doc.width + 50, doc.height + 50)
        
        # Patrón decorativo en las esquinas
        canvas.setLineWidth(2)
        corner_size = 20
        # Esquina superior izquierda
        canvas.line(15, doc.height + 70, 15 + corner_size, doc.height + 70)
        canvas.line(15, doc.height + 70, 15, doc.height + 70 - corner_size)
        # Esquina superior derecha
        canvas.line(doc.width + 70, doc.height + 70, doc.width + 70 - corner_size, doc.height + 70)
        canvas.line(doc.width + 70, doc.height + 70, doc.width + 70, doc.height + 70 - corner_size)
        # Esquina inferior izquierda
        canvas.line(15, 15, 15 + corner_size, 15)
        canvas.line(15, 15, 15, 15 + corner_size)
        # Esquina inferior derecha
        canvas.line(doc.width + 70, 15, doc.width + 70 - corner_size, 15)
        canvas.line(doc.width + 70, 15, doc.width + 70, 15 + corner_size)
        
        canvas.restoreState()

    # Configurar estilos
    styles = getSampleStyleSheet()
    
    # Agregar estilos personalizados
    styles.add(ParagraphStyle(
        name="Titulo", 
        fontSize=36, 
        alignment=TA_CENTER, 
        textColor=colors.HexColor("#5B3E1D"), 
        leading=42,
        fontName="Helvetica-Bold"
    ))
    
    styles.add(ParagraphStyle(
        name="Subtitulo", 
        fontSize=14, 
        alignment=TA_CENTER, 
        spaceAfter=6,
        textColor=colors.HexColor("#7A5A2B")
    ))
    
    styles.add(ParagraphStyle(
        name="Nombre", 
        fontSize=34, 
        alignment=TA_CENTER, 
        leading=38,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#2C3E50")
    ))
    
    styles.add(ParagraphStyle(
        name="Texto", 
        fontSize=12, 
        alignment=TA_CENTER, 
        leading=16,
        textColor=colors.HexColor("#34495E")
    ))
    
    styles.add(ParagraphStyle(
        name="FirmaNombre", 
        fontSize=16, 
        alignment=TA_CENTER, 
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#2C3E50")
    ))
    
    styles.add(ParagraphStyle(
        name="FirmaLabel", 
        fontSize=12, 
        alignment=TA_CENTER,
        textColor=colors.HexColor("#7F8C8D")
    ))
    
    styles.add(ParagraphStyle(
        name="Pie", 
        fontSize=9, 
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#95A5A6")
    ))
    
    styles.add(ParagraphStyle(
        name="NumeroCertificado", 
        fontSize=10, 
        alignment=TA_CENTER,
        textColor=colors.HexColor("#7F8C8D"),
        fontName="Helvetica-Bold"
    ))

    # Construir el contenido del PDF
    story = []



    # Espacio inicial
    story.append(Spacer(1, 40))

    # Número de certificado único
    story.append(Paragraph(f"Nº: {numero_certificado}", styles["NumeroCertificado"]))
    story.append(Spacer(1, 20))
    
    # Logo 
    try:
        logo_paths = [
            "static/images/logo.png",
            "static/images/logo.jpg", 
            "static/logo.png",
            os.path.join(os.path.dirname(__file__), "..", "static", "images", "logo.png")
        ]
        
        logo_path = None
        for path in logo_paths:
            if os.path.exists(path):
                logo_path = path
                break
                
        if logo_path:
            logo = Image(logo_path, width=2*inch, height=0.8*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
    except Exception as e:
        current_app.logger.warning(f"Logo no cargado: {e}")

    # Espacio inicial
    story.append(Spacer(1,10))
    # Título y encabezado
    story.append(Paragraph("CERTIFICADO", styles["Titulo"]))
    story.append(Paragraph("DE PARTICIPACIÓN", styles["Subtitulo"]))
    story.append(Spacer(1, 18))

    # Línea "Este certificado se otorga a"
    story.append(Paragraph("Este certificado se otorga a", styles["Subtitulo"]))
    story.append(Spacer(1, 8))

    # Nombre grande del participante
    story.append(Paragraph(f"<b>{nombre_participante}</b>", styles["Nombre"]))
    
    # Documento de identidad (si existe)
    if row.get('documento_id'):
        story.append(Paragraph(f"Documento: {row['documento_id']}", styles["Subtitulo"]))
    
    story.append(Spacer(1, 14))

    # Texto principal
    fecha_fin = row['fecha_fin']
    if hasattr(fecha_fin, 'strftime'):
        fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
    else:
        fecha_fin_str = str(fecha_fin).split()[0]
        
    texto = (f"En reconocimiento por su valiosa participación en el {row['tipo_evento']} "
             f"<b>\"{row['evento']}\"</b>, finalizado el {fecha_fin_str}.")
    story.append(Paragraph(texto, styles["Texto"]))
    story.append(Spacer(1, 50))

    # Firma del organizador
    story.append(Spacer(1, 30))
    story.append(Paragraph(org_nombre, styles["FirmaNombre"]))
    story.append(Paragraph("_____________________________", styles["FirmaLabel"]))
    story.append(Paragraph("Firma del organizador", styles["FirmaLabel"]))
    story.append(Spacer(1, 40))

    # Pie con fecha de emisión
    fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Emitido: {fecha_emision}", styles["Pie"]))

    # Construir PDF con borde
    doc.build(story, onFirstPage=add_border, onLaterPages=add_border)
    buf.seek(0)
    
    # Guardar número de certificado en la base de datos
    try:
        cert_existente = q_one("SELECT id_certificado FROM certificados WHERE id_inscripcion=%s", (insc_id,))
        if not cert_existente:
            q_exec("""
                INSERT INTO certificados (id_inscripcion, fecha_emision, numero_serie)
                VALUES (%s, NOW(), %s)
            """, (insc_id, numero_certificado))
    except Exception as e:
        current_app.logger.error(f"Error guardando certificado en BD: {e}")

    # ENVIAR CERTIFICADO POR CORREO
    # En la función certificado, después de generar el PDF, reemplaza esta parte:

  # ENVIAR NOTIFICACIÓN SOLO SI EL EVENTO HA TERMINADO Y NO HA SIDO NOTIFICADO
    evento_terminado = row.get('evento_terminado', 0)
    certificado_notificado = row.get('certificado_notificado', 0)
    
    if evento_terminado and not certificado_notificado:
        try:
            from utils.mailer import enviar_notificacion_certificado_disponible
            from models.inscripcion import marcar_certificado_notificado
            from models.user import User
            
            # Crear objeto usuario para el correo
            usuario_correo = User(
                id_usuario=row['uid'],
                nombre=row['usu_nombre'],
                apellido=row.get('usu_apellido', ''),
                correo=row['correo'],
                contrasena='',
                celular=None,
                documento_id=row.get('documento_id'),
                created_at=None,
                activo=1,
                rol_id=1
            )
            
            # Enviar notificación
            enviar_notificacion_certificado_disponible(
                usuario=usuario_correo,
                evento=row,
                inscripcion=row,
                porcentaje=porcentaje_actual
            )
            
            # Marcar como notificado
            marcar_certificado_notificado(insc_id)
            
        except Exception as e:
            current_app.logger.error(f"Error enviando notificación de certificado: {e}")

    # NO enviar certificado por correo automáticamente - solo cuando el usuario lo descarga
    # Crear una nueva copia del buffer para la descarga
    buf_download = BytesIO(buf.getvalue())
    buf_download.seek(0)

    return send_file(
        buf_download, 
        as_attachment=True,
        download_name=f"certificado_{row['evento'].replace(' ', '_')}_{insc_id}.pdf", 
        mimetype="application/pdf"
    )
    

# funcion de generar qr
try:
    from utils.qr_generator import generar_qr_asistencia as generar_qr_func, validar_token_qr
except ImportError:
    # Si no existe el archivo, define funciones básicas
    def generar_qr_func(eid, duracion_minutos=120):
        return None
    def validar_token_qr(token, eid):
        return False

#ruta degeneracion de QR
@eventos_bp.route("/<int:eid>/generar_qr_asistencia")
@role_required(2, 3)
def generar_qr_asistencia_page(eid):  # ← CAMBIAR NOMBRE
    """Página para generar QR de asistencia"""
    # Verificar permisos del evento
    ev = MEvento.obtener(eid)
    if not ev:
        abort(404)
    if current_user.rol_id == 3 and ev["id_organizador"] != current_user.id:
        flash("No puedes generar QR para este evento.", "danger")
        return redirect(url_for("eventos.eventos_list"))
    
    # Generar QR usando la función importada
    qr_data = generar_qr_func(eid)  # ← Usar la función importada
    
    if not qr_data:
        flash("Error al generar el código QR.", "danger")
        return redirect(url_for("eventos.asistencia", eid=eid))
    
    return render_template("events/qr_asistencia.html", 
                         ev=ev, 
                         qr_data=qr_data,
                         ahora=datetime.now())
    
#ruta para validar los tokens de los QR
@eventos_bp.route("/<int:eid>/escanear_qr/<token>")
@login_required
def escanear_qr_asistencia(eid, token):
    """Procesa el escaneo del QR y marca asistencia automáticamente"""
    ev = MEvento.obtener(eid)
    if not ev:
        flash("Evento no encontrado.", "danger")
        return redirect(url_for("publico.inicio_publico"))
    
    # Verificar que el usuario está inscrito
    from models.inscripcion import esta_inscrito
    inscripcion = esta_inscrito(eid, current_user.id)
    if not inscripcion:
        flash("No estás inscrito en este evento.", "warning")
        return redirect(url_for("eventos.evento_detalle", eid=eid))
    
    # Validar token QR
    if not validar_token_qr(token, eid):
        flash("Código QR inválido o expirado.", "danger")
        return redirect(url_for("eventos.evento_detalle", eid=eid))
    
    # Validar horario del evento
    from datetime import datetime, time
    ahora = datetime.now()
    hora_actual = ahora.time()
    
    # Solo permitir marcar asistencia dentro del horario del evento
    if ev.get('hora_inicio_diaria') and ev.get('hora_fin_diaria'):
        if hora_actual < ev['hora_inicio_diaria'] or hora_actual > ev['hora_fin_diaria']:
            flash(f"❌ Fuera del horario del evento. Solo puedes marcar asistencia entre {ev['hora_inicio_diaria'].strftime('%H:%M')} y {ev['hora_fin_diaria'].strftime('%H:%M')}.", "warning")
            return redirect(url_for("eventos.evento_detalle", eid=eid))
    
    # Marcar asistencia para hoy
    hoy = ahora.date()
    
    # Verificar si ya tiene asistencia marcada hoy
    from models.db import q_one
    asistencia_existente = q_one(
        "SELECT id_asistencia FROM asistencias WHERE id_evento=%s AND id_usuario=%s AND fecha=%s",
        (eid, current_user.id, hoy)
    )
    
    if asistencia_existente:
        flash("✅ Ya tenías asistencia marcada para hoy.", "info")
    else:
        # Insertar nueva asistencia
        from models.db import q_exec
        q_exec(
            "INSERT INTO asistencias (id_evento, id_usuario, fecha, asistio, activo) VALUES (%s, %s, %s, 1, 1)",
            (eid, current_user.id, hoy)
        )
        
        # Actualizar la inscripción para marcar que asistió
        q_exec(
            "UPDATE inscripciones SET asistio=1, updated_at=CURRENT_TIMESTAMP WHERE id_evento=%s AND id_usuario=%s",
            (eid, current_user.id)
        )
        
        flash("🎉 ¡Asistencia marcada correctamente!", "success")
    
    return redirect(url_for("eventos.evento_detalle", eid=eid))