# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models, exceptions, _
from datetime import date, datetime

class Approvers(models.Model):
    """ mail_approvers holds the data related to the approve mechanism inside
    Evosoft. The administrator can assign Partners or channels to approve documents (records) of any kind
    that inherits from mail.thread and mail.approve. Documents approvers will receive
    notifications for new records to approve. If a channel is assigned as approver, any member of the channel can
     approve the related document. A subscription is characterized by:

    :param: res_model: model of the objects to approve
    :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.approvers'
    _inherit = ['mail.approval','mail.thread']
    _rec_name = 'user_id'
    _log_access = False
    _description = 'Record Approvers'
    _order = 'sequence, id'

    '''
    def _default_sequence(self):
        seq = self.env['mail.approvers']
        print(self)
        record = self.sudo().search([('res_id', '=', self.res_id), ('res_model', '=', self.res_model)], order='sequence desc', limit=1)
        print('get sequence')
        if record:
            return record.sequence + 10
        else:
            return 100
    '''

    # Note. There is no integrity check on model names for performance reasons.
    # However, approvers of unlinked models are deleted by models themselves
    # (see 'ir.model' inheritance).
    res_model = fields.Char(
        'Related Document Model Name', index=True)
    res_id = fields.Integer(
        'Related Document ID', index=True, help='Id of the resource to approve')
    user_id = fields.Many2one(
        'res.users', string='Related User', ondelete='restrict', index=True)
    sequence = fields.Integer(help="Sequence defined for the approval workflow.", default=100)
    approval_type = fields.Many2one('mail.activity.type', string='Activity Type', required=True, ondelete='restrict',
                                    domain=[('category', '=', 'approval')])
    state = fields.Selection([
        ('new', 'New'),
        ('review', 'Under Review'),
        ('hold', 'Hold'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved'),],
        string='Status', readonly=False, copy=True, index=True, default='new')
    state_date = fields.Datetime(string='State Date', readonly=True)
    approval_mail_activity = fields.Many2one('mail.activity', string='Activity', required=False)

    #
    # Modifying approvers change access rights to individual documents. As the
    # cache may contain accessible/inaccessible data, one has to refresh it.
    #

    mail_message_id = fields.Many2one('mail.message', string='Feedback Message')

    @api.onchange('user_id', 'approval_type')
    def onchange_approver_value(self):
        if self.state == 'review':
            self.state = 'new'

    @api.multi
    def _invalidate_documents(self):
        """ Invalidate the cache of the documents followed by ``self``. """
        for record in self:
            if record.res_id:
                self.env[record.res_model].invalidate_cache(ids=[record.res_id])

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Approvers, self).create(vals_list)
        res._invalidate_documents()
        # todo Call function to create related record in "mail.approvers.approvals"
        return res

    @api.multi
    def write(self, vals):
        if 'res_model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        res = super(Approvers, self).write(vals)
        if any(x in vals for x in ['res_model', 'res_id', 'user_id']):
            self._invalidate_documents()
        return res

    @api.multi
    def unlink(self):
        self._invalidate_documents()
        # todo Call function to remove the related record in "mail.approvers.approvals"
        return super(Approvers, self).unlink()

    @api.multi
    def validate_approver(self):
        self.ensure_one()
        current_user = self.env.uid
        if self.user_id.id != current_user:
            print('You are updating the status of a record assigned to %s on his or her behalf.' % self.user_id.name)
            # todo raise message to let the user know he is approving a record for someone else
        return current_user

    @api.multi
    def approver_approve(self, mail_message_id=False):
        for rec in self:
            print('mail msg = %s' % mail_message_id)
            rec.update_state(state='approved', mail_message_id=mail_message_id)

    @api.multi
    def approver_reject(self, mail_message_id=False):
        for rec in self:
            rec.update_state(state='rejected', mail_message_id=mail_message_id)

    @api.multi
    def approver_hold(self, mail_message_id=False):
        for rec in self:
            rec.update_state(state='hold', mail_message_id=mail_message_id)

    @api.multi
    def update_state(self, state, mail_message_id=False):
        self.ensure_one()
        user_id = self.validate_approver()
        vals = {
            'state_date': datetime.now(),
            'state': state,
            'user_id': user_id,
            'mail_message_id': mail_message_id,
        }
        self.write(vals)

    def update_approver_state(self, activity_id):
        if activity_id:
            approver_id = self.env['mail.activity'].browse(activity_id)
            if approver_id.activity_type_id.category == 'approval':
                if approver_id.user_id.id != self._uid:
                    raise exceptions.ValidationError("Approval activities can only be updated by the activity owner.") 
            if approver_id.mail_approver_id:
                approver_id.mail_approver_id.state_date = datetime.now()
                if self._context.get('accept_btn'):
                        approver_id.mail_approver_id.state = 'approved'
                        print('Approved 1')
                elif self._context.get('reject_btn'):
                        approver_id.mail_approver_id.state = 'rejected'
                        approver_id.mail_approver_id.mail_approval_state = 'rejected'
                        print('Rejected 1')
                elif self._context.get('hold_btn'):
                        approver_id.mail_approver_id.state = 'hold'
                        approver_id.mail_approver_id.mail_approval_state = 'hold'
                        print('Hold 1')

    _sql_constraints = [
        ('mail_approvers_res_user_res_model_id_uniq', 'unique(res_model,res_id,user_id,approval_type)',
         'Error, a user cannot follow twice the same object.'),
    ]


    # --------------------------------------------------
    # Private tools action_window functions
    # --------------------------------------------------

    @api.multi
    def act_window_display_approver(self, res_model, res_id):
        res = {
            'name': 'Approvers',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.approvers',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 10,
            'domain': [
                ('res_model', '=', res_model),
                ('res_id', '=', res_id)
            ],
            'context': {
                'default_res_model': res_model,
                'default_res_id': res_id,
            },
        }
        return res


class Approval_type(models.Model):
    _name = 'mail.approvers_type'
    _description = 'Approval Type'
    _order = 'id desc'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)
    is_active = fields.Boolean('Active', default=False)
    model_ids = fields.Many2many('ir.model', string='Models')


class MailDefaultApprovers(models.Model):
    _name = 'mail.default_approvers'
    _description = 'Approval Type'
    _order = 'id desc'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)
    is_active = fields.Boolean('Active', default=False)
    res_model = fields.Char(
        'Related Document Model Name', required=True, index=True)


class Mail_activity(models.Model):
    _inherit = 'mail.activity'

    mail_approver_id = fields.Many2one('mail.approvers', string='Approver')
    # todo: on model mail.activity, add function Accept, Reject and pause
    # function accept will run mail_approver_id.update_state(state='approve')
    # function reject will run mail_approver_id.update_state(state='reject')
    # function hold will run mail_approver_id.update_state(state='hold')
