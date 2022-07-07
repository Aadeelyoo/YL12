import base64
import io
import re
import json
import time
from PyPDF2 import PdfFileReader, PdfFileWriter
from pikepdf import Pdf

from reportlab.pdfgen import canvas
from tempfile import NamedTemporaryFile, TemporaryFile

from odoo import tools
from odoo.tools.translate import _

class pdf2:
    def process_from_stack(self):
        # writer = PdfFileWriter()
        pdf = Pdf.new()
        font = "Helvetica"
        normal_font_size = 14
        metadata = {
            u'/Version' : 'PDF-1.5'
        }
        for document in self:
            try:
                src = Pdf.open(io.BytesIO(base64.b64decode(document)))
                pdf.pages.extend(src.pages)
                # reader = PdfFileReader(io.BytesIO(base64.b64decode(document)), strict=False, overwriteWarnings=False)
            except Exception as e:
                print("Reader Error: ",e)
                continue

            # width = float(reader.getPage(0).mediaBox.getUpperRight_x())
            # height = float(reader.getPage(0).mediaBox.getUpperRight_y())
            #
            # header = io.BytesIO()
            # can = canvas.Canvas(header)
            # can.setFont(font, normal_font_size)
            # can.setFillColorRGB(1, 0, 0)
            #
            #
            # # can.drawCentredString(width / 2, height - normal_font_size, text_to_print)
            # can.save()
            # header_pdf = PdfFileReader(header, overwriteWarnings=False)
            # for page_number in range(0, reader.getNumPages()) :
            #     page = reader.getPage(page_number)
            #     try:
            #         page.mergePage(header_pdf.getPage(0))
            #         writer.addPage(page)
            #     except Exception as e:
            #         print("-------------------------error aya hay",e)

        # if not writer.getNumPages():
        #     raise Exception(_('There is no pdf attached to generate a claim report.'))

        _buffer = io.BytesIO()
        pdf.save(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        return merged_pdf
        # pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(merged_pdf))]
        #
        # return request.make_response(merged_pdf, headers=pdfhttpheaders)

tools.adobe_merge = pdf2
