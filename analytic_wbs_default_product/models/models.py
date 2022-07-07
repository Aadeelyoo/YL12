# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AnalyticWbsOrderLineProductDefault(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _get_product_default(self):
        default_product = self.env.ref('analytic_wbs.product_product_cost_control')
        if default_product:
            return default_product.id
    
    product_id = fields.Many2one(default=_get_product_default)


class AnalyticWbsTciLineProductDefault(models.Model):
    _inherit = 'tci.line'

    @api.model
    def _get_product_default(self):
        default_product = self.env.ref('analytic_wbs.product_product_cost_control')
        if default_product:
            return default_product.id

    product_id = fields.Many2one(default=_get_product_default)


class AnalyticWbsTciTemplateLineProductDefault(models.Model):
    _inherit = 'tci.template.line'

    @api.model
    def _get_product_default(self):
        default_product = self.env.ref('analytic_wbs.product_product_cost_control')
        if default_product:
            return default_product.id

    product_id = fields.Many2one(default=_get_product_default)
