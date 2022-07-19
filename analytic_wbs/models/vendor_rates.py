# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import osv


class ResParter(models.Model):

    _inherit = "res.partner"

    def action_vendor_price(self):
        view_tree_id = self.env.ref('analytic_wbs.product_supplierinfo_tree_view_vendor_price').id
        context = self._context.copy()
        action = {
            'name': _('Vendor Price List'),
            'view_mode': 'tree,form',
            'view_id' : view_tree_id,
            'views': [
                [view_tree_id, "list"]
            ],
            'res_model': 'product.supplierinfo',
            'type': 'ir.actions.act_window',
            'context': context,
            'nodestroy' : True,
            'target' : 'current',
            'domain': [('name', '=', self.id)],
        }
        return action

class ResParter(models.Model) :
    _inherit = "purchase.order"

    def action_vendor_approved_rates(self):
        view_tree_id = self.env.ref('analytic_wbs.product_supplierinfo_tree_view_vendor_price').id
        context = self._context.copy()
        action = {
            'name' : _('Approved Rates'),
            'view_mode' : 'tree,form',
            'view_id' : view_tree_id,
            'views' : [
                [view_tree_id, "list"]
            ],
            'res_model' : 'product.supplierinfo',
            'type' : 'ir.actions.act_window',
            'context' : context,
            'nodestroy' : True,
            'target' : 'current',
            'domain' : [('name', '=', self.partner_id.id)],
        }
        return action

