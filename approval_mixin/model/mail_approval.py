# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models, exceptions
import datetime


class AbstractMailAprovers(models.AbstractModel):
    _name = 'mail.approval'

    mail_is_approver = fields.Boolean(
        'Is Approver', compute='_compute_is_approver', search='_search_is_approver')
    mail_approver_ids = fields.One2many(
        'mail.approvers', 'res_id', string='Approvers', domain=lambda self: [('res_model', '=', self._name)])
    mail_user_ids = fields.Many2many(
        comodel_name='res.users', string='Approvers (Users)',
        compute='_get_approvers', search='_search_approver_users')

    mail_approver_count = fields.Integer('Approver Count', compute='_compute_approver_count')
    mail_approver_count_approved = fields.Integer('Approved Count', compute='_compute_approver_count')
    mail_approver_count_rejected = fields.Integer('Rejected Count', compute='_compute_approver_count')
    mail_approver_count_hold = fields.Integer('Hold Count', compute='_compute_approver_count')
    mail_approval_start_date = fields.Datetime(string='Approval Start Date', readonly=True, copy=False)
    mail_approval_end_date = fields.Datetime(string='Approval End Date', readonly=True, copy=False)
    mail_approval_state = fields.Selection([
        ('new', 'New'),
        ('review', 'Under Review'),
        ('hold', 'On Hold'),
        ('stop', 'Stopped'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')],
        string='Approval Status', copy=False, index=True, default='new', compute='_compute_approval_state')
    mail_approval_current_user_id = fields.One2many('res.users', compute='_get_approver_current_user_id')

    approval_document_ids = fields.Many2many('ir.attachment', string='Approval Documents', copy=False)
    #approval_report_id = fields.Many2one('ir.attachment', string='Approval Report', copy=False)
    approval_report_name = fields.Char(string='Approval Report Name')
    approval_report_id = fields.Binary(attachment=True, string='Approval Report', copy=False)

    current_user_approval_required = fields.Boolean(string="Approval Required", compute='_compute_approval_required',
                                                    search="_search_appr_req")

    def get_current_user_approval_activity_ids(self):
        self.ensure_one()
        user_id = self.env.uid
        appr_activity_ids = self.env['mail.activity'].search([('res_id', '=', self.id), ('res_model', '=', self._name),
                                                              ('user_id', '=', user_id), ('category', '=', 'approval')])
        return appr_activity_ids

    def _compute_approval_required(self):
        user_id = self.env.uid
        for rec in self:
            appr_activity = self.env['mail.activity'].search([('res_id', '=', rec.id), ('res_model', '=', self._name),
                                                              ('user_id', '=', user_id), ('category', '=', 'approval')])
            if appr_activity:
                res = True
            else:
                res = False
            rec.current_user_approval_required = res

    @api.model
    def _search_appr_req(self, operator, value):
        # Assumes operator is '=' or '!=' and value is True or False
        res_model = self._name
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()

        res = self.env[res_model].search([('current_user_approval_required', operator, value)])

        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', [r[0] for r in res])]

    '''
	todo Rules of approbation to be set-up on the PO
	todo Template for rule of approbation
	'''

    @api.one
    @api.depends('mail_approver_ids')
    def _get_approvers(self):
        self.mail_user_ids = self.mail_approver_ids.mapped('user_id')

    @api.one
    @api.depends('mail_approver_ids.state')
    def _compute_approval_state(self):
        for record in self:
            approvers_obj = record.mail_approver_ids

            if not approvers_obj:
                new_state = False
            else:
                approved_users = approvers_obj.search(
                    [('id', 'in', record.mail_approver_ids.ids), ('state', '=', 'approved')])

                if not record.mail_approval_start_date:
                    new_state = 'new'
                if record.mail_approval_start_date and not record.mail_approval_end_date:
                    rejected_count = record.mail_approver_count_rejected
                    hold_count = record.mail_approver_count_hold

                    if rejected_count:
                        new_state = 'rejected'
                    elif hold_count:
                        new_state = 'hold'
                    elif approvers_obj == approved_users:
                        new_state = 'approved'
                    else:
                        new_state = 'review'
                if record.mail_approval_start_date and record.mail_approval_end_date:
                    if approvers_obj == approved_users:
                        new_state = 'approved'
                    else:
                        new_state = 'stop'

            record.mail_approval_state = new_state

    @api.model
    def _get_approver_current_user_id(self):
        for record in self:
            approvers = record.mail_approver_ids.sudo().search([
                ('state', 'in', ['new', 'hold']), ('res_id', '=', record.id)], order='sequence asc', limit=1)
            if approvers:
                if approvers.user_id:
                    res = approvers.user_id
                else:
                    res = False
                record.mail_approval_current_user_id = res

    @api.multi
    def get_mail_approval_next_user_id(self):
        self.ensure_one()
        user_reject = self.mail_approver_count_rejected
        user_hold = self.mail_approver_count_hold

        if user_reject:
            self.mail_approval_state = 'rejected'
            next_user = self.create_uid
        elif user_hold:
            self.mail_approval_state = 'hold'
            user_holding = self.mail_approver_ids.search([('id', 'in', self.mail_approver_ids.ids),
                                                          ('state', '=', 'hold')], limit=1)
            next_user = user_holding.user_id
        elif not user_reject or not user_hold:
            user_approved = self.mail_approver_ids.search([('id', 'in', self.mail_approver_ids.ids),
                                                           ('state', '=', 'approved')])
            if self.mail_approver_ids == user_approved:
                next_user = self.create_uid
            else:
                to_review = self.mail_approver_ids.search([('id', 'in', self.mail_approver_ids.ids),
                                                           ('state', '=', 'review')], limit=1)
                if to_review:
                    next_user = to_review.user_id
                if not to_review:
                    next_user = self.create_uid
        else:
            next_user = self.create_uid

        return next_user

    @api.model
    def _search_approver_users(self, operator, operand):
        """
		Search function for mail_approver_ids
		Do not use with operator 'not in'. Use instead mail_is_approvers
		"""
        # todo Make it work with not in
        assert operator != "not in", "Do not search mail_approver_ids with 'not in'"
        approvers = self.env['mail.approvers'].sudo().search([
            ('res_model', '=', self._name),
            ('user_id', operator, operand)])
        # using read() below is much faster than approvers.mapped('res_id')
        return [('id', 'in', [res['res_id'] for res in approvers.read(['res_id'])])]

    @api.multi
    @api.depends('mail_approver_ids')
    def _compute_is_approver(self):
        approvers = self.env['mail.approvers'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('user_id', '=', self.env.user.id),
        ])
        # using read() below is much faster than approvers.mapped('res_id')
        following_ids = [res['res_id'] for res in approvers.read(['res_id'])]
        for record in self:
            record.mail_is_approver = record.id in following_ids

    @api.model
    def _search_is_approver(self, operator, operand):
        approvers = self.env['mail.approvers'].sudo().search([
            ('res_model', '=', self._name),
            ('user_id', '=', self.env.user.id),
        ])
        # Cases ('mail_is_approver', '=', True) or  ('mail_is_approver', '!=', False)
        if (operator == '=' and operand) or (operator == '!=' and not operand):
            # using read() below is much faster than approvers.mapped('res_id')
            return [('id', 'in', [res['res_id'] for res in approvers.read(['res_id'])])]
        else:
            # using read() below is much faster than approvers.mapped('res_id')
            return [('id', 'not in', [res['res_id'] for res in approvers.read(['res_id'])])]

    @api.multi
    def action_mail_approval_start(self):
        if self:
            res_id = self.id
            res_model = self._name
        elif self._context:
            # read model and Id from context
            res_id = self._context.get('default_res_id')
            res_model = self._context.get('default_model')

        if res_id and res_model:
            record = self.env[res_model].browse(res_id)
            mail_approvers = self.env['mail.approvers'].search([('res_id', '=', res_id), ('res_model', '=', res_model)])
            if not mail_approvers:
                raise exceptions.ValidationError('Approvers must be added before to start the approval process.')
            elif record:
                if not record.mail_approval_start_date:
                    record.mail_approval_start_date = datetime.datetime.now()

            mail_activity = self.env['mail.activity']
            res_model_id = self.env['ir.model'].search([('model', '=', res_model)])
            if record.mail_approval_state in ('new', 'review'):
                if mail_approvers:
                    approver_ids = []
                    for approver in reversed(mail_approvers):
                        if approver.user_id:
                            approver_ids.append(approver.id)
                            approval_activity_ids = self.env['mail.activity'].search(
                                [('res_id', '=', res_id), ('res_model', '=', res_model), ('mail_approver_id', '=', approver.id)])
                            for activity in approval_activity_ids:
                                if activity.user_id != approver.user_id or activity.activity_type_id != approver.approval_type:
                                    activity.unlink()
                            if approver.state == 'new' or not approver.state:
                                vals = {
                                    'activity_type_id': approver.approval_type.id,
                                    'date_deadline': datetime.datetime.now(),
                                    'user_id': approver.user_id.id,
                                    'res_id': res_id,
                                    'res_model': res_model,
                                    'res_model_id': res_model_id.id,
                                    'mail_approver_id': approver.id,
                                }
                                new_mail_activity = mail_activity.create(vals)
                                approver.state = 'review'
                                approver.approval_mail_activity = new_mail_activity.id
                    # Check for superceeded activity and delete
                    superceded_approval_activity_ids = self.env['mail.activity'].search([('res_id', '=', res_id),
                                                                                         ('res_model', '=', res_model),
                                                                                         ('mail_approver_id', 'not in', approver_ids)])
                    if superceded_approval_activity_ids:
                        superceded_approval_activity_ids.unlink()

                    next_user = record.get_mail_approval_next_user_id()
                    record.user_id = next_user
                    record.mail_approval_state = 'review'

            if record.mail_approval_state == 'approved':
                raise exceptions.ValidationError("The current record is already approved by all approvers.")

    @api.multi
    def action_mail_approval_pause(self):
        print('approval pause')
        for record in self:
            print('approval pause')
            '''
			if record.mail_approver_ids:
				# do something
			else:
				raise exceptions.ValidationError('Approvers must be added before to start the approval process.')
			'''

    @api.multi
    def action_mail_approval_stop(self):
        for record in self:
            res_id = record.id
            res_model = record._name
            # Check for superceeded activity and delete
            superceded_approval_activity_ids = self.env['mail.activity'].search([('res_id', '=', res_id),
                                                                                 ('res_model', '=', res_model),])
            if superceded_approval_activity_ids:
                superceded_approval_activity_ids.unlink()

            '''
			if record.mail_approver_ids:
				# do something
				print('approval stop')
			else:
				raise exceptions.ValidationError('Approvers must be added before to start the approval process.')
			'''

    @api.multi
    def _compute_approver_count(self):
        read_group_var = self.env['mail.approvers'].read_group(
            [('res_id', 'in', self.ids), ('res_model', '=', self._name)],
            fields=['res_id'],
            groupby=['res_id'])
        approver_count_dict = dict((d['res_id'], d['res_id_count']) for d in read_group_var)
        for record in self:
            record.mail_approver_count = approver_count_dict.get(record.id, 0)
            record.mail_approver_count_approved = record.mail_approver_ids.sudo().search_count([
                ('state', '=', 'approved'),
                ('res_id', '=', record.id)
            ])
            record.mail_approver_count_rejected = record.mail_approver_ids.sudo().search_count([
                ('state', '=', 'rejected'),
                ('res_id', '=', record.id)
            ])
            record.mail_approver_count_hold = record.mail_approver_ids.sudo().search_count([
                ('state', '=', 'hold'),
                ('res_id', '=', record.id)
            ])

    @api.multi
    def action_mail_edit_approver(self):
        res_model = self._name
        res_id = self.id
        return self.env['mail.approvers'].act_window_display_approver(res_model=res_model, res_id=res_id)

    def _track_subtype(self, init_values):
        if 'approval_ids' in init_values:
            return 'mail.mt_comment'
        return False

    def custom_search_count(self, res_id=False, res_model=False):
        if not res_id or not res_model:
            approved_count = 0
            rejected_count = 0
            total_count = 0
        else:
            approved_count = self.env['mail.approvers'].sudo().search_count([
                ('state', '=', 'approved'),
                ('res_id', '=', res_id),
                ('res_model', '=', res_model),
            ])

            rejected_count = self.env['mail.approvers'].sudo().search_count([
                ('state', '=', 'rejected'),
                ('res_id', '=', res_id),
                ('res_model', '=', res_model),
            ])
            total_count = self.env['mail.approvers'].sudo().search_count([
                ('res_id', '=', res_id),
                ('res_model', '=', res_model),
            ])
        vals = {
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'total_count': total_count,
        }
        return vals
