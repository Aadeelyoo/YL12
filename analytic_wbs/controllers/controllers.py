# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class analytic_wbs(http.Controller):

	@http.route(['/tci/approval_report/<int:record_id>'], type='http', auth="public", website=True, sitemap=False)
	def tci_approval_report(self, **kw):
		record_id = kw['record_id']
		if record_id:
			url = "/web#id=%r&model=purchase.order&view_type=form"%record_id
			return request.redirect(url)

	@http.route(['/po'], type='http', auth="user", website=True, sitemap=False)
	def http_request_purchasse_order(self, **kw):
		if kw.get('internalref'):
			order = request.env['purchase.order'].sudo().search([('internal_ref', '=', kw.get('internalref'))])
			if order:
				url = "/web#id=%s&model=purchase.order&view_type=form" % (order.id)
				return request.redirect(url)
			else:
				url = '/web'
				return request.redirect(url)
		else:
			url = '/web'
			return request.redirect(url)

	@http.route(['/employee'], type='http', auth="user", website=True, sitemap=False)
	def http_request_employee(self, **kw):
		if kw.get('id'):
			employee = request.env['hr.employee'].sudo().search([('id', '=', kw.get('id'))])
			if employee:
				url = "/web#id=%s&model=hr.employee&view_type=form" % (employee.id)
				return request.redirect(url)
			else:
				url = '/web'
				return request.redirect(url)
		else:
			url = '/web'
			return request.redirect(url)

	@http.route(['/partner'], type='http', auth="user", website=True, sitemap=False)
	def http_request_partner(self, **kw):
		if kw.get('id'):
			partner = request.env['res.partner'].sudo().search([('id', '=', kw.get('id'))])
			if partner:
				url = "/web#id=%s&model=res.partner&view_type=form" % (partner.id)
				return request.redirect(url)
			else:
				url = '/web'
				return request.redirect(url)
		else:
			url = '/web'
			return request.redirect(url)

	@http.route(['/projectwbs'], type='http', auth="user", website=True, sitemap=False)
	def http_request_project_wbs(self, **kw):
		if kw.get('id'):
			pwbs = request.env['account.analytic_wbs.project'].sudo().search([('id', '=', kw.get('id'))])
			if pwbs:
				url = "/web#id=%s&model=account.analytic_wbs.project&view_type=form" % (pwbs.id)
				return request.redirect(url)
			else:
				url = '/web'
				return request.redirect(url)
		else:
			url = '/web'
			return request.redirect(url)