# -*- coding: utf-8 -*-
from odoo import http

# class AnalyticWbsSummary(http.Controller):
#     @http.route('/analytic_wbs_summary/analytic_wbs_summary/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_wbs_summary/analytic_wbs_summary/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_wbs_summary.listing', {
#             'root': '/analytic_wbs_summary/analytic_wbs_summary',
#             'objects': http.request.env['analytic_wbs_summary.analytic_wbs_summary'].search([]),
#         })

#     @http.route('/analytic_wbs_summary/analytic_wbs_summary/objects/<model("analytic_wbs_summary.analytic_wbs_summary"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_wbs_summary.object', {
#             'object': obj
#         })