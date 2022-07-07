# Create merged attahments
@api.multi
def create_merged_pdf(self):
    for rec in self:
        if not rec.batch_id:
            # generate pdf name
            pdf_name = str('Document Review Report - ') + str(rec.reference) + str(' - ') + str(rec.name) + str('.pdf')
            rec.approval_report_name = pdf_name
            # Commenting Watermark work
            # water_mark_pdf
            # water_mark_pdf_data = []
            # water_mark_pdf = self.env.ref('analytic_wbs.report_for_solevo_tci_header').sudo().render_qweb_pdf([rec.id])[0]
            # water_mark_pdf_data.append(water_mark_pdf)

            # merger report
            decoded_data = []
            pdf_report = self.env.ref('analytic_wbs.report_for_solevo_tci_reportt').sudo().render_qweb_pdf([rec.id])[0]
            decoded_data.append(pdf_report)
            attachment_ids = rec.approval_document_ids

            writer = PdfFileWriter()
            font = "Helvetica"
            normal_font_size = 14

            for att in attachment_ids:
                # decoded_data.append(base64.b64decode(att.datas))
                '''
                #merged_pdf_report = pdf.merge_pdf(decoded_data)
                # write watermark and merged report
                # pdf_writer = PdfFileWriter()
                # counter = 0
                # for page in PdfFileReader(BytesIO(merged_pdf_report)).pages:
                #     watermark_page = pdf_writer.addBlankPage(
                #         page.mediaBox.getWidth(), page.mediaBox.getHeight()
                #     )
                #     watermark_page.mergePage(page)
                #     if counter != 0:
                #         watermark_page.mergePage(PdfFileReader(BytesIO(water_mark_pdf_data[0])).pages[0])
                #     counter += 1
                # pdf_content = BytesIO()
                # pdf_writer.write(pdf_content)
                # attachments = [(pdf_name, pdf_content.getvalue())]
                '''

                try:
                    reader = PdfFileReader(io.BytesIO(base64.b64decode(att.datas)), strict=False,
                                           overwriteWarnings=False)
                except Exception:
                    continue

                header = io.BytesIO()
                can = canvas.Canvas(header)
                can.setFont(font, normal_font_size)
                can.setFillColorRGB(1, 0, 0)

                can.save()
                header_pdf = PdfFileReader(header, overwriteWarnings=False)
                for page_number in range(0, reader.getNumPages()):
                    page = reader.getPage(page_number)
                    try:
                        page.mergePage(header_pdf.getPage(0))
                        writer.addPage(page)

                    except Exception:
                        continue

            _buffer = io.BytesIO()
            writer.write(_buffer)
            merged_pdf = _buffer.getvalue()
            _buffer.close()

            print(merged_pdf)
            report = merged_pdf

            '''
            try:
                report = base64.b64encode(pdf.merge_pdf(decoded_data))
            except AttributeError:
                continue
            '''

            # search for existing attachments for the field
            attach_ids = self.env['ir.attachment'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id),
                                                           ('res_field', '=', 'approval_report_id')])
            if attach_ids:
                attach_ids.unlink()

            ir_values = {
                'name': pdf_name,
                'type': 'binary',
                'datas': report,
                'res_model': rec._name,
                'datas_fname': pdf_name,
                'res_id': rec.id,
                'res_field': 'approval_report_id',
                'mimetype': 'application/pdf',
            }
            self.env['ir.attachment'].create(ir_values)

            rec.message_post(body="Document Review Report Created")
            '''
            rec.message_post(body="Validation Report Created", attachments=attachments)
            rec.approval_report_id = rec.attachment_ids.search([('name', '=', pdf_name),
                                                                  ('res_model','=','tci'),
                                                                  ('res_id','=',rec.id),
                                                                  ], limit=1).id
            '''
        else:
            print('no report created')