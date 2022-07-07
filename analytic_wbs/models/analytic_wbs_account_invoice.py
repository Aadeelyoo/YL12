# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
import odoo.addons.decimal_precision as dp


class wbsAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    project_id = fields.Many2one('project.project', string='Project', required=False, ondelete='restrict', track_visibility='onchange')
    workticket_line_ids = fields.One2many('purchase.workticket.line', 'invoice_id', string='LEM Lines', readonly=True,
        states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, copy=False)
    workticket_ids = fields.One2many('purchase.workticket', 'invoice_id', string='LEMs', readonly=True,
        states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, copy=False)
    wt_total_untaxed_amount = fields.Float(string='Untaxed Amount', store=True,
        compute='_compute_wt_amount', digits=dp.get_precision('Account'))
    wt_total_tax_amount = fields.Float(string='Tax Amount', store=True,
        compute='_compute_wt_amount', digits=dp.get_precision('Account'))
    wt_total_amount = fields.Float(string='Total Amount', store=True,
        compute='_compute_wt_amount', digits=dp.get_precision('Account'))

    @api.one
    @api.depends('workticket_ids.untaxed_amount', 'currency_id', 'company_id', 'date')
    def _compute_wt_amount(self):
        self.wt_total_untaxed_amount = sum(line.untaxed_amount for line in self.workticket_ids)
        self.wt_total_tax_amount = sum(line.total_tax_amount for line in self.workticket_ids)
        self.wt_total_amount = self.wt_total_untaxed_amount + self.wt_total_tax_amount


    @api.model
    def _prepare_invoice_line_from_po_line(self, line):
        if line.product_id.purchase_method == 'purchase':
            qty = line.product_qty - line.qty_invoiced
        else:
            qty = line.qty_received - line.qty_invoiced
        if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
            qty = 0.0
        taxes = line.taxes_id
        invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes)
        invoice_line = self.env['account.invoice.line']
        data = {
            'purchase_line_id': line.id,
            'name': line.order_id.name+': '+line.name,
            'origin': line.order_id.origin,
            'uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
            'account_id': invoice_line.with_context({'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
            'price_unit': line.order_id.currency_id.compute(line.price_unit, self.currency_id, round=False),
            'quantity': qty,
            'discount': 0.0,
            'account_analytic_id': line.account_analytic_id.id,
            'account_project_id': line.account_project_id.id,
            'analytic_tag_ids': line.analytic_tag_ids.ids,
            'invoice_line_tax_ids': invoice_line_tax_ids.ids
        }
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, self.env.user.company_id)
        if account:
            data['account_id'] = account.id
        return data

class wbsAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=False,
                                         ondelete='restrict')
    project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
