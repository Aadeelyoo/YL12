# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime

class WbsSapGrDump(models.Model):
    _name = 'sap.gr_line_dump'
    _description = 'SAP GR Lines Dump'
    _order = 'document_date desc'

    # Data dump fields from SAP
    purchasing_doc = fields.Char('Purchasing Document')
    sap_item = fields.Integer('Item')
    material_document = fields.Char('Material Document')
    reference = fields.Char('Reference')
    amount_loc_crcy = fields.Float('Amount Local Currency')
    document_date = fields.Date('Document Date')
    posting_date = fields.Date('Posting Date')
    short_text = fields.Char('Short Text')

    @api.multi
    def ir_action_update_sap_mapped_invoice_no(self):
        # update invoice no and tci no
        for rec in self:
            if rec.reference:
                domain = [
                    ('purchasing_document', '=', rec.purchasing_doc),
                    ('ref_document_number', '=', rec.material_document),
                    ('document_header_text', '=', False)
                ]
                mapped_actual_id = self.env['sap.actuals_line_mapped'].search(domain)
                if mapped_actual_id:
                    for line in mapped_actual_id:
                        comment = str('invoice no update auto ') + str(datetime.now().date())
                        vals = {
                            'document_header_text': rec.reference,
                            'comment': comment,
                        }
                        line.write(vals)

        # search outstanding tci_lines and map the invoice number
        tci_line_ids = self.env['tci.line'].search([('description', '=', False), ('tci_type', '=', 'act')])
        for tci_line in tci_line_ids:
            doc_no = tci_line.tci_id.actual_mapped_id.document_header_text
            if doc_no:
                tci_line.description = doc_no
