# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, exceptions
from odoo.exceptions import UserError
import datetime


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('approval', 'Record Approval')])


class MailActivity(models.Model):
    _inherit = "mail.activity"

    category = fields.Selection(related='activity_type_id.category', store=True)

    # Accept Button Method
    def action_feedback(self, feedback=False):
        message = self.env['mail.message']
        if isinstance(feedback, str):
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            if activity.activity_type_id.category == 'approval':
                record.message_post_with_view(
                    'approval_mixin.activity_approver_msg_done',
                    values={'activity': activity},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
            else:
                record.message_post_with_view(
                    'mail.message_activity_done',
                    values={'activity': activity},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
            message |= record.message_ids[0]
        self.action_record_change_approval_state(action_type='approve', mail_message_id=message.ids[0])
        self.unlink()
        return message.ids and message.ids[0] or False

    def action_record_change_approval_state(self, action_type=False, mail_message_id=False):
        for activity in self:
            if action_type:
                if activity.activity_type_id.category == 'approval':
                    record = self.env[activity.res_model].browse(activity.res_id)
                    if action_type not in ('approve','reject','hold'):
                        raise exceptions.ValidationError('action type not defined in function action_record_before_unlink')
                    if action_type == 'approve':
                        activity.mail_approver_id.approver_approve(mail_message_id=mail_message_id)
                    if action_type == 'reject':
                        activity.mail_approver_id.approver_reject(mail_message_id=mail_message_id)
                    if action_type == 'hold':
                        activity.mail_approver_id.approver_hold(mail_message_id=mail_message_id)

                    if record:
                        record.user_id = record.get_mail_approval_next_user_id()
                        # Validate if all mail_approver_ids have been approved
                        approved_users = record.mail_approver_ids.search([('id', 'in', record.mail_approver_ids.ids),
                                                                           ('state', '=', 'approved')])
                        approvers = record.mail_approver_ids

                        if approvers == approved_users:
                            record.mail_approval_end_date = datetime.datetime.now()

    # Hold Button Method
    def action_record_hold(self):
        message = self.env['mail.message']
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            if activity.activity_type_id.category == 'approval':
                record.message_post_with_view(
                    'approval_mixin.activity_approver_msg_hold',
                    values={'activity': activity},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
            message |= record.message_ids[0]

        self.action_record_change_approval_state(action_type='hold', mail_message_id=message.ids[0])
        self.unlink()
        return message.ids and message.ids[0] or False

    # Reject Button Done Method
    def action_record_reject(self, feedback=False, delete_all=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            if activity.activity_type_id.category == 'approval':
                record.message_post_with_view(
                    'approval_mixin.activity_approver_msg_reject',
                    values={'activity': activity},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
                # TODO: Acc action to trigger the email back to the vendor and add feedback to the email
            else:
                record.message_post_with_view(
                    'mail.message_activity_done',
                    values={'activity': activity},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity.activity_type_id.id,
                )
            message |= record.message_ids[0]

        self.action_record_change_approval_state(action_type='reject', mail_message_id=message.ids[0])
        if delete_all == True:
            # get all outstanding approval activities and unlink them
            act_to_delete_ids = self.env['mail.activity'].search([('res_model', '=', self.res_model),
                                                                 ('res_id', '=', self.res_id),
                                                                 ('category', '=', 'approval')])
            act_to_delete_ids.unlink()
        else:
            self.unlink()
        return message.ids and message.ids[0] or False

    @api.multi
    def action_notify(self):
        body_template = self.env.ref('mail.message_activity_assigned')
        for activity in self:
            # do not send email for approval activity type
            if not activity.activity_category == 'approval':
                model_description = self.env['ir.model']._get(activity.res_model).display_name
                body = body_template.render(
                    dict(activity=activity, model_description=model_description),
                    engine='ir.qweb',
                    minimal_qcontext=True
                )
                self.env['mail.thread'].message_notify(
                    partner_ids=activity.user_id.partner_id.ids,
                    body=body,
                    subject=_('%s: %s assigned to you') % (
                    activity.res_name, activity.summary or activity.activity_type_id.name),
                    record_name=activity.res_name,
                    model_description=model_description,
                    notif_layout='mail.mail_notification_light'
                )