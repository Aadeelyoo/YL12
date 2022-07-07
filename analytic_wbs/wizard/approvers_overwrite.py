# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ApproversOverwrite(models.TransientModel):

	_name = "approvers_overwrite"
	_description = "Approvers Overwrite"

	msg = fields.Char(string='Message')
	tci_template_id = fields.Many2one('tci.template', string='Document Template')
	tci_id = fields.Many2one('tci', string='TCI')
	po_id = fields.Many2one('purchase.order', string='Purchase Order')
	vendor_id = fields.Many2one(related='po_id.partner_id', string='Vendor')

	@api.multi
	def update_approvers(self):
		search_id = self.env['tci'].search([('id','=',self._context.get('default_tci_id'))])
		if search_id:
			self.tci_id = search_id.id
			if self.msg:
				return search_id.create_tmpl_approvers(search_id.id, 'tci',True, self._context.get('approvers'))
			if self.tci_template_id:
				search_id.write({'tci_template_id':self.tci_template_id.id})
			return search_id.get_template_approvers()