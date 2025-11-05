# utils/pdf_generator.py
from flask import current_app
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import os

def generar_pdf_certificado(usuario, evento, inscripcion):
    """Genera el PDF del certificado (extraído de la función certificado)"""
    try:
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

        # Logo (si existe)
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
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
        except Exception as e:
            current_app.logger.warning(f"Logo no cargado: {e}")

        # Espacio inicial
        story.append(Spacer(1, 40))

        # Número de certificado único
        numero_certificado = f"CERT-{inscripcion['id_inscripcion']}-{datetime.now().strftime('%Y%m%d')}"
        story.append(Paragraph(f"Nº: {numero_certificado}", styles["NumeroCertificado"]))
        story.append(Spacer(1, 20))

        # Título y encabezado
        story.append(Paragraph("CERTIFICADO", styles["Titulo"]))
        story.append(Paragraph("DE PARTICIPACIÓN", styles["Subtitulo"]))
        story.append(Spacer(1, 18))

        # Línea "Este certificado se otorga a"
        story.append(Paragraph("Este certificado se otorga a", styles["Subtitulo"]))
        story.append(Spacer(1, 8))

        # Nombre grande del participante
        nombre_participante = f"{usuario.nombre} {usuario.apellido or ''}".strip()
        story.append(Paragraph(f"<b>{nombre_participante}</b>", styles["Nombre"]))
        
        # Documento de identidad (si existe)
        if usuario.documento_id:
            story.append(Paragraph(f"Documento: {usuario.documento_id}", styles["Subtitulo"]))
        
        story.append(Spacer(1, 14))

        # Texto principal
        fecha_fin = evento['fecha_fin']
        if hasattr(fecha_fin, 'strftime'):
            fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        else:
            fecha_fin_str = str(fecha_fin).split()[0]
            
        texto = (f"En reconocimiento por su valiosa participación en el {evento['tipo_evento']} "
                 f"<b>\"{evento['nombre']}\"</b>, finalizado el {fecha_fin_str}.")
        story.append(Paragraph(texto, styles["Texto"]))
        story.append(Spacer(1, 50))

        # Firma del organizador
        org_nombre = (f"{evento.get('org_nombre') or ''} {evento.get('org_apellido') or ''}").strip() or "Organizador"
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
        
        return buf
            
    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {str(e)}")
        return None