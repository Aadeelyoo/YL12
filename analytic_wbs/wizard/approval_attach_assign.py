# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ApproversAttachAssign(models.TransientModel):

	_name = "approval_attach_assign"
	_description = "Approval Attachment Assignation"

	tci_id = fields.Many2one('tci', string='TCI')
	approval_document_ids = fields.Many2many('ir.attachment',string='Approval Documents')

	@api.multi
	def update_attachments(self):
		search_id = self.env['tci'].search([('id','=',self._context.get('default_tci_id'))])
		if search_id:
			search_id.write({
				'approval_document_ids':[(6,0,self.approval_document_ids.ids)],
				'check_approval_process':True,
				})
			return search_id.action_mail_approval_start()