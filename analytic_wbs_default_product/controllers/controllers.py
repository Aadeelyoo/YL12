# -*- coding: utf-8 -*-
from odoo import http

# class AnalyticWbsDefaultProduct(http.Controller):
#     @http.route('/analytic_wbs_default_product/analytic_wbs_default_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_wbs_default_product/analytic_wbs_default_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_wbs_default_product.listing', {
#             'root': '/analytic_wbs_default_product/analytic_wbs_default_product',
#             'objects': http.request.env['analytic_wbs_default_product.analytic_wbs_default_product'].search([]),
#         })

#     @http.route('/analytic_wbs_default_product/analytic_wbs_default_product/objects/<model("analytic_wbs_default_product.analytic_wbs_default_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_wbs_default_product.object', {
#             'object': obj
#         })