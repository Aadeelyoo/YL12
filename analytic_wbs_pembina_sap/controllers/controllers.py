# -*- coding: utf-8 -*-
from odoo import http

# class AnalyticWbsPembinaSap(http.Controller):
#     @http.route('/analytic_wbs_pembina_sap/analytic_wbs_pembina_sap/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytic_wbs_pembina_sap/analytic_wbs_pembina_sap/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytic_wbs_pembina_sap.listing', {
#             'root': '/analytic_wbs_pembina_sap/analytic_wbs_pembina_sap',
#             'objects': http.request.env['analytic_wbs_pembina_sap.analytic_wbs_pembina_sap'].search([]),
#         })

#     @http.route('/analytic_wbs_pembina_sap/analytic_wbs_pembina_sap/objects/<model("analytic_wbs_pembina_sap.analytic_wbs_pembina_sap"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytic_wbs_pembina_sap.object', {
#             'object': obj
#         })