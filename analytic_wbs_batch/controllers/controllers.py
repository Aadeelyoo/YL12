# -*- coding: utf-8 -*-
from odoo import http

# class AnalyticWbsBatch(http.Controller):
#     @http.route('/analytic_wbs_batch/analytic_wbs_batch/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_wbs_batch/analytic_wbs_batch/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_wbs_batch.listing', {
#             'root': '/analytic_wbs_batch/analytic_wbs_batch',
#             'objects': http.request.env['analytic_wbs_batch.analytic_wbs_batch'].search([]),
#         })

#     @http.route('/analytic_wbs_batch/analytic_wbs_batch/objects/<model("analytic_wbs_batch.analytic_wbs_batch"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_wbs_batch.object', {
#             'object': obj
#         })