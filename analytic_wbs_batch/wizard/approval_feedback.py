# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BatchApproversFeedback(models.TransientModel) :
    _name = "batch_approval_feedback"
    _description = "Approval Feedback"

    batch_id = fields.Many2one('tci.batch', string='Batch')
    approval_feedback = fields.Char(string='Feedback')
    action = fields.Char(string='Action')

    @api.multi
    def confirm_reject(self) :
        batch_id = self.env['tci.batch'].search([('id', '=', self._context.get('default_batch_id'))])
        if batch_id and self.action == 'rejected' :
            batch_id.action_batch_reject(feedback=self.approval_feedback)
            return batch_id

    @api.multi
    def confirm_approve(self) :
        batch_id = self.env['tci.batch'].search([('id', '=', self._context.get('default_batch_id'))])
        if batch_id and self.action == 'approved' :
            return batch_id.action_batch_approve(feedback=self.approval_feedback)
        else :
            return False
