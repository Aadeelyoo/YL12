# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ApproversFeedback(models.TransientModel):

	_name = "approval_feedback"
	_description = "Approval Feedback"

	tci_id = fields.Many2one('tci', string='TCI')
	approval_feedback = fields.Char(string='Feedback')
	action = fields.Char(string='Action')

	@api.multi
	def confirm_reject(self):
		tci_id = self.env['tci'].search([('id', '=', self._context.get('default_tci_id'))])
		if tci_id and self.action == 'reject':
			tci_id.action_tci_reject(feedback=self.approval_feedback)
			return tci_id.send_by_email()

	@api.multi
	def confirm_approve(self):
		tci_id = self.env['tci'].search([('id', '=', self._context.get('default_tci_id'))])
		if tci_id and self.action == 'approve':
			return tci_id.action_tci_approve(feedback=self.approval_feedback)
		else:
			return False

