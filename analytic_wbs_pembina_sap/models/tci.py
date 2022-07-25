# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class Tci(models.Model):
    _inherit = "tci"

    workflow_mapped_id = fields.Many2one('workflow.invoice_mapped', string='Workflow Invoice', required=False,
                                         readonly=False)
    actual_mapped_id = fields.Many2one('sap.actuals_line_mapped', string='SAP Actual', required=False,
                                       readonly=False)
    @api.multi
    def ir_action_link_actuals_to_invoice(self):
        i = 0
        for rec in self:
            # This function only works with act type tci
            if rec.tci_type != 'act':
                raise UserError(_("This action only works with TCI type actuals"))
            else:
                # Get description listed in the tci lines
                descr = set()
                act_descr = self.env['tci.line'].search_read([('tci_id', '=', rec.id)], ['description'])
                for line in act_descr:
                    if line['description'] and line['description'] not in descr:
                        descr.add(line['description'])

                if len(descr) != 0:
                    descr_trunc = set()
                    for x in descr:
                        dlen = len(x)
                        descr_trunc . add(x[4:dlen])
                    descript_list = list(descr.union(descr_trunc))
                    # search matching invoices
                    domain = [
                        ('po_id', '=', rec.po_id.id),
                        ('tci_type', '=', 'inv'),
                        ('state', '!=', 'void'),
                        ('reference', 'in', descript_list),
                    ]
                    invoice_ids = self.env['tci'].search(domain)
                    if len(invoice_ids) == 1 and not rec.parent_invoice_act_rel_id:
                        rec.parent_invoice_act_rel_id = invoice_ids[0].id

                else:
                    domain2 = [
                        ('po_id', '=', rec.po_id.id),
                        ('tci_type', '=', 'inv'),
                        ('state', '!=', 'void'),
                        ('untaxed_amount', '=', rec.untaxed_amount),
                    ]
                    invoice_ids = self.env['tci'].search(domain2)
                    if len(invoice_ids) == 1 and not rec.parent_invoice_act_rel_id:
                        rec.parent_invoice_act_rel_id = invoice_ids[0].id

                if not rec.parent_invoice_act_rel_id:
                    # Search for all actuals and all invoices for 1 particular document date and validate full value
                    if rec.actual_mapped_id:
                        document_date = rec.actual_mapped_id.document_date
                        domain_actual_mapped = [
                            ('purchase_order_id', '=', rec.po_id.id),
                            ('document_date', '=', document_date),
                        ]
                        all_actual_mapped_ids = self.env['sap.actuals_line_mapped'].search(domain_actual_mapped)

                        sum_actual = sum(line.val_ca_area_crcy for line in all_actual_mapped_ids)
                        domain_invoice = [
                            ('po_id', '=', rec.po_id.id),
                            ('tci_type', '=', 'inv'),
                            ('state', '!=', 'void'),
                            ('date', '=', document_date),
                        ]
                        all_invoice_ids = self.env['tci'].search(domain_invoice)
                        sum_invoice = sum(line.untaxed_amount for line in all_invoice_ids)

                        if len(all_invoice_ids) == 1 and sum_actual == sum_invoice:
                            invoice_id = all_invoice_ids[0]
                            all_actual_ids = []
                            for line in all_actual_mapped_ids:
                                if line.tci_id.id not in all_actual_ids:
                                    all_actual_ids.append(line.tci_id.id)
                            actual_ids = self.env['tci'].browse(all_actual_ids)
                            for rec in actual_ids:
                                if not rec.parent_invoice_act_rel_id == invoice_id:
                                    rec.parent_invoice_act_rel_id = invoice_id.id