from pikepdf import Pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from io import BytesIO

def create_watermark(watermark_text):
    watermark_io = BytesIO()
    c = canvas.Canvas(watermark_io, pagesize=letter)

    transparent_color = Color(0, 0, 0, alpha=0.1)
    c.setFillColor(transparent_color)

    c.saveState()
    c.translate(300, 400)
    c.rotate(45)
    c.setFont("Helvetica", 100)
    c.drawCentredString(0, 0, watermark_text)
    c.restoreState()

    c.save()
    watermark_io.seek(0)
    return watermark_io

def apply_text_watermark(input_pdf, watermark_text):
    watermark_io = create_watermark(watermark_text)
    output_pdf_io = BytesIO()

    with Pdf.open(input_pdf) as main_pdf, Pdf.open(watermark_io) as watermark_pdf:
        watermark_page = watermark_pdf.pages[0]

        for page in main_pdf.pages:
            page.add_overlay(watermark_page)

        main_pdf.save(output_pdf_io)

    output_pdf_io.seek(0)
    return output_pdf_io
