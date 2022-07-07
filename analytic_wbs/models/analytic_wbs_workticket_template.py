# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class purchase_wttemplate_line(models.Model):
    _name = 'purchase.wttemplate.line'
    _description = 'wttemplate Line'
    _order = 'line_order asc'
    _rec_name = 'description'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    description = fields.Char('Description', required=True)
    qty = fields.Float('Quantity', default=1.0)
    uom = fields.Many2one('uom.uom', string='UOM', required=True)
    unit_rate = fields.Float('Unit Rate', default=0.0)
    line_order = fields.Integer(string='Order')

    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')
    wttemplate_id = fields.Many2one('purchase.wttemplate', 'wttemplate no', required=True, ondelete='cascade')

    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State", readonly=True, store=True)
    po_id = fields.Many2one(related="wttemplate_id.po_id", string='Purchase Order', readonly=True)

    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        for record in self:
            # get purchase.order.line account_project_ids
            order_line_ids = self.env['purchase.order.line'].search([('order_id', '=', record.po_id.id)])
            project_wbs_ids = []
            for line in order_line_ids:
                wbs = line.account_project_id
                if wbs.id not in project_wbs_ids:
                    project_wbs_ids.append(wbs.id)
            res['domain'] = {
                'account_project_id': [('id', 'in', project_wbs_ids)],
                }
        return res


class purchase_wttemplate(models.Model):
    _name = 'purchase.wttemplate'
    _description = 'Workticket Template'
    _order = 'id desc'
    _rec_name = 'name'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Name', required=True)
    wttemplate_line_ids = fields.One2many('purchase.wttemplate.line', 'wttemplate_id', string='Work Ticket Template Lines')

    user_id = fields.Many2one('res.users', string='Created By', default=_default_user, track_visibility='onchange')
    po_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, track_visibility='onchange')

    active = fields.Boolean('Active', index=True, default=True)
    default_template = fields.Boolean('Use as Default Template', index=True, default=False)

class wttemplate_purchase_order(models.Model):

    _inherit = "purchase.order"
    wttemplate_ids = fields.One2many('purchase.wttemplate', 'po_id', string='Work Ticket Templates')
