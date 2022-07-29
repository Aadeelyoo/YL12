# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError, Warning



class ResUsers(models.Model):
    _inherit = ['res.users']

    digital_initial = fields.Binary(string='Digital Initials',
                                      attachment=True)


class DocApprovalLines(models.Model):
    _name = 'doc.approval.line'
    _description = 'Document Approval Lines'

    res_users = fields.Many2one('res.users', string='User', readonly=True, required=True)
    display_name = fields.Char(related='res_users.display_name')
    color = fields.Integer('Color Index', default=0)
    digital_signature = fields.Binary(related='res_users.digital_signature')
    user_image = fields.Binary(related='res_users.image')
    sign_date = fields.Date(string='Date', default=fields.Date.context_today)
    res_id = fields.Integer(string='Resource ID')
    res_model = fields.Char(srting='Model Name')
    approval_type = fields.Selection([
        ('rate', 'Rate Validated'),
        ('quantity', 'Quantity Validated'),
        ('overall', 'Overall Validated')
    ], string='Approval Type', copy=False, index=True, readonly=True, store=True,
        help="Status of the line.", track_visibility='onchange')


class DocApproval(models.AbstractModel):
    _name = 'doc.approval'
    _description = 'Document Approval'

    approval_ids = fields.One2many(
        'doc.approval.line', 'res_id', string='Approvals',
        domain=lambda self: [('res_model', '=', self._name)], auto_join=True, track_visibility=True)
    approval_line_count = fields.Integer('Attachment Count', compute='_compute_approval_line_count')

    # todo Rules of approbation to be set-up on the PO
    # todo Template for rule of approbation
    # todo Gestion de l'approbation des work tickets
    # todo Gestion de l'approbation des RFI, ECN, VCR

    # todo Gestion de l'approbation to be done by Model
    '''
    fewfew
    '''

    # todo Approbation avec renvoi automatique è la personne suivante selon la séquence

    @api.multi
    def _compute_approval_line_count(self):
        read_group_var = self.env['doc.approval.line'].read_group([('res_id', 'in', self.ids),
                                                                   ('res_model', '=', self._name)],
                                                                  fields=['res_id'],
                                                                  groupby=['res_id'])

        approval_count_dict = dict((d['res_id'], d['res_id_count']) for d in read_group_var)
        for record in self:
            record.approval_line_count = approval_count_dict.get(record.id, 0)

    @api.multi
    def prepare_vals(self, type):
        self.ensure_one
        if not self.state == 'submitted':
            raise ValidationError("The document must be in the submitted state to activate the validation process.")
        else:
            context = self._context
            current_uid = context.get('uid')
            vals = {
                'res_users': current_uid,
                'res_id': self.id,
                'res_model': self._name,
                'approval_type': type,
            }
            return vals

    @api.multi
    def action_doc_log_validation_rate(self):
        vals = self.prepare_vals(type='rate')
        return self.action_doc_log_approval(vals)

    @api.multi
    def action_doc_log_validation_quantity(self):
        vals = self.prepare_vals(type='quantity')
        return self.action_doc_log_approval(vals)

    @api.multi
    def action_doc_log_validation_overall(self):
        vals = self.prepare_vals(type='overall')
        return self.action_doc_log_approval(vals)

    @api.multi
    def action_doc_log_approval(self, vals):
        # Verify if the doc is already approved by the user
        search_domain = []
        for key in vals.keys():
            search_domain.append((key, '=', vals[key]))
        exist_rec = self.env['doc.approval.line'].search(search_domain)

        if not exist_rec:
            new_rec = self.env['doc.approval.line'].create(vals)
            message = ('The document was correctly validated for %s.' % new_rec.approval_type)
            self.message_post(body=message, subject="Document Validation", subtype="mt_note")
        else:
            print('user already approved the document')

    def _track_subtype(self, init_values):
        if 'approval_ids' in init_values:
            return 'mail.mt_comment'
        return False