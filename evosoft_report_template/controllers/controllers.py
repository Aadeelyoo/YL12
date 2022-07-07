# -*- coding: utf-8 -*-
from odoo import http

# class EvosoftReportTemplate(http.Controller):
#     @http.route('/evosoft_report_template/evosoft_report_template/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/evosoft_report_template/evosoft_report_template/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('evosoft_report_template.listing', {
#             'root': '/evosoft_report_template/evosoft_report_template',
#             'objects': http.request.env['evosoft_report_template.evosoft_report_template'].search([]),
#         })

#     @http.route('/evosoft_report_template/evosoft_report_template/objects/<model("evosoft_report_template.evosoft_report_template"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('evosoft_report_template.object', {
#             'object': obj
#         })