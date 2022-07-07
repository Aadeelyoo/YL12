# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import osv
from odoo import tools
from odoo.tools import pike_pdf_merge
from collections import defaultdict

import base64
import re
import math
from odoo.exceptions import UserError
from odoo.tools import pdf
import odoo.addons.decimal_precision as dp
from logging import getLogger
logger = getLogger(__name__)

try:
    from PyPDF2 import PdfFileWriter, PdfFileReader  # pylint: disable=W0404
    from PyPDF2.utils import PdfReadError  # pylint: disable=W0404
except ImportError:
    logger.debug('Can not import PyPDF2')


class TciBatch(models.Model):
    _name = 'tci.batch'
    _description = 'Tci Batch'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'mail.approval']
    _order = 'name desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    @api.model
    def _default_name(self):
        seq_id = self.env['ir.sequence'].get('tci.batch.number')
        return self.env.context.get('name', seq_id)

    name = fields.Char('Name', required=True, default=_default_name, track_visibility='onchange', translate=True)
    description = fields.Char('Description', required=False)
    batch_type_id = fields.Many2one('tci.batch_type', 'Batch Type', required=False, ondelete='restrict')
    tci_ids = fields.One2many('tci', 'batch_id', string='Batch Items')
    #tci_batch_analytic_project_ids = fields.One2many('tci.analytic.project', 'tci_id', related='tci_ids.analytic_project_line_ids', string='Analytic Items')
    #tci_batch_analytic_project_ids = fields.Many2many('tci_batch_analytic_project_sql', compute='_compute_tci_analytic_ids', string='Analytic Items')
    tci_batch_analytic_project_ids = fields.One2many('tci_batch_analytic_project_sql', 'batch_id', compute='_compute_tci_analytic_ids', string='Analytic Items')
    # todo Change selection fields value for something more related to the SOW status (with approval process) Include status included on PO
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Information Validated'),
        ('review', 'Submitted for Approval'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
    ], default='draft', track_visibility='onchange', string='Status')

    po_id = fields.Many2one(comodel_name='purchase.order', string='Purchasse Order', ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', track_visibility='onchange')

    user_id = fields.Many2one('res.users', string='Assigned to', default=_default_user, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    external_ref = fields.Char('External Reference', required=False)
    external_ref_file_name = fields.Char('External File Name', copy=False)
    external_ref_file = fields.Binary(attachment=True, string='External File',
                                      help="This field holds external reference file.", copy=False)

    barcode = fields.Char(string='Barcode')

    tci_count = fields.Integer(compute='_compute_tci_count', string='Item Count')

    approval_report_ids = fields.Many2many('ir.attachment', string='Approval Reports', copy=False,
                                           compute='_compute_attachment')
    approval_report_count = fields.Integer(compute='_compute_attachment', string='Approval Report Count')

    batch_report_name = fields.Char('Batch Report Name', copy=False)
    batch_report_document = fields.Binary(attachment=True, string='Batch Report final Doc', copy=False)
    batch_report_document_temp = fields.Binary(attachment=True, string='Batch Report Temporary File', copy=False)

    total_amount = fields.Monetary(string='Total Amount', compute='compute_amount', store=True)

    check_approval_process = fields.Boolean(
        string='Check Approval Process',
    )
    approval_method = fields.Selection([('1', 'Approval Mechanism'),('2', 'Approval FIORI')], compute='_check_approval_method')


    @api.model
    def _check_approval_method(self):
        for rec in self:
            rec.approval_method = False
            if rec.state == 'validated':
                if not rec.external_ref:
                    rec.approval_method = '2'
                if rec.external_ref and rec.external_ref_file:
                    rec.approval_method = '1'

    @api.depends('tci_ids', 'tci_ids.untaxed_amount')
    def compute_amount(self):
        for rec in self:
            rec.total_amount = sum(line.untaxed_amount for line in rec.tci_ids)

    @api.model
    def _compute_tci_analytic_ids(self):
        for batch in self:
            #print('Searching for batch id = %s' % batch.id)
            recs = self.env['tci_batch_analytic_project_sql'].search([('batch_id', '=', batch.id)])
            #print('returned records = %s' % recs)
            #for x in recs:
            #    print('returned batch id from recs = %s' % x.batch_id)
            batch.tci_batch_analytic_project_ids = recs.ids


    @api.multi
    def _compute_attachment(self):
        for rec in self:
            domain = [
                ('res_model', '=', 'tci'),
                ('res_id', 'in', rec.tci_ids.ids),
                ('res_field', '=', 'approval_report_id')
            ]
            rec.approval_report_ids = self.env['ir.attachment'].search(domain).ids
            rec.approval_report_count = len(rec.approval_report_ids)

    @api.multi
    def _compute_tci_count(self):
        for record in self:
            record.tci_count = len(record.tci_ids)

    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        for record in self:
            # validate if partner_id is the owner of the PO, if not, change vendor
            po_id = record.po_id
            if po_id:
                if not po_id.partner_id.id == record.partner_id.id:
                    record.partner_id = po_id.partner_id.id
                    # todo: change domain of tasks to get only those related to the PO
                res['domain'] = {
                    'tci_ids': [('po_id', '=', po_id.id), ('batch_id', '=', False)],
                }
            else:
                res['domain'] = {
                    'tci_ids': [('batch_id', '=', False)],
                }

        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = {}
        for record in self:
            # validate if po_id and task_ids are relevant to this partner, if not, change it.
            partner = record.partner_id
            po = record.po_id

            if partner:
                partner_pos = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
                if po:
                    if not po.partner_id.id == partner.id:
                        record.po_id = False
                res['domain'] = {
                    'po_id': [('id', 'in', partner_pos.ids)],
                    'tci_ids': [('partner_id', '=', partner.id), ('batch_id', '=', False)],
                }

            if not partner:
                res['domain'] = {
                    'po_id': [],
                    'tci_ids': [('batch_id', '=', False)],
                }
        return res


    @api.multi
    def batch_draft(self):

        for approver in self.mail_approver_ids:
            approver.state = 'new'
        self.write({
            'mail_approval_start_date': False,
            'mail_approval_end_date': False,
            'mail_approval_state': False,
            'approval_report_id': False,
        })

        res_model_id = self.env['ir.model'].search([('model', '=', self._name)]).id
        activity = self.env['mail.activity'].search([('res_model_id', '=', res_model_id), ('res_id', '=', self.id)])
        if activity :
            activity.unlink()

        self.message_post(body="State reset to Draft")

        self.write({'state': 'draft' })
        return True

    @api.multi
    def batch_submitted(self):
        self.ensure_one()
        if not self.batch_report_document_temp:
            raise UserError(
                _('Please add the attachment file prior to submit the record for approval. Attachment must be in a .PDF format'))
        else:
            attach_ids = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id),
                                                           ('res_field', 'in',
                                                            ['batch_report_document', 'batch_report_document_temp'])])

            self.approval_document_ids = attach_ids
            self.approval_document_id = attach_ids
            self.action_mail_approval_start()
            self.check_approval_process = True
            self.state = 'review'


    @api.multi
    def batch_validate(self):
        rec_to_validate = {}
        rec_msg = {}
        for rec in self:
            msg_val = {}
            po_ids = []
            rejected_tci = []
            doc_missing = []
            for tci in rec.tci_ids:
                # validate all tci are on the same PO
                po_ids.append(tci.po_id.id)
                if not tci.approval_report_id:
                    doc_missing.append(tci.name)
                if tci.state == 'rejected':
                    rejected_tci.append(tci.name)
            if len(set(po_ids)) > 1:
                 msg_val = {
                     'Listed POs': 'The LEMs attached to the batch are related to more than one PO.'
                                   ' Only LEMs from the same Po can be batched together.',
                 }
            if rejected_tci:
                msg_val = {
                    'State': 'Please remove the following LEMs from the batch as they have been rejected. %s' % rejected_tci,
                }
            if doc_missing:
                msg = str('Approval Doc missing for %s' % doc_missing)
                msg_val.update({'Approval Document': msg})
            if msg_val:
                rec_msg[rec.name] = msg_val
            if not msg_val:
                rec_to_validate[rec] = {
                    'state': 'validated',
                }
        if rec_msg:
            raise osv.except_osv(('Batch not Validated'), ('%s' % rec_msg))
        if rec_to_validate:
            for key in rec_to_validate:
                key.write(rec_to_validate[key])
                key.create_bach_report_pdf()


        '''
        self.write({'state': 'validated'})
        return True
        '''
    @api.multi
    def action_batch_approve_fiori(self):
        self.ensure_one()
        # if not self.external_ref:
        #     raise osv.except_osv(('Information Required'), ('External reference number required'))
        # if not self.external_ref:
        #     raise osv.except_osv(('Information Required'), ('External File required'))

        self.write({'state' : 'approved'})

    @api.multi
    def action_batch_approve(self, feedback=False):
        self.ensure_one()

        activity_ids = self.get_current_user_approval_activity_ids()
        for activity in activity_ids:
            activity.action_feedback(feedback=feedback)

        if self.mail_approval_state == 'approved':
            self.write({'state' : 'approved'})
            self.create_bach_report_pdf()
        return True


    @api.multi
    def action_batch_approve_with_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'batch_approval_feedback',
            'view_id': self.env.ref('analytic_wbs_batch.batch_approval_feedback_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_batch_id': self.id,
                'default_action': 'approved',
            },
            'target': 'new',
        }


    @api.multi
    def action_batch_reject_with_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'batch_approval_feedback',
            'view_id': self.env.ref('analytic_wbs_batch.batch_approval_feedback_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_batch_id': self.id,
                'default_action': 'rejected',
            },
            'target': 'new',
        }

    @api.multi
    def action_batch_reject(self, feedback=False):
        self.ensure_one()
        activity_ids = self.get_current_user_approval_activity_ids()
        for activity in activity_ids[0]:
            activity.action_record_reject(feedback=feedback, delete_all=True)

        if self.mail_approval_state == 'rejected':
            self.write({'state' : 'rejected'})
            self.create_bach_report_pdf()

    @api.multi
    def batch_posted(self):
        if not self.external_ref_file_name:
            raise UserError("Please Provide External File.")
        self.create_bach_report_pdf(final=True)
        self.write({'state': 'posted'})
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.external_ref:
                raise osv.except_osv(('Error'), ('Batch with External Reference numbers can not be deleted'))
        return super(TciBatch, self).unlink()

    '''
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values:
            return 'project.mt_progrtrans_stage'
        return super(TciBatch, self)._track_subtype(init_values)
    '''

    # Overriding Create Method
    @api.model
    def create(self, vals):
        res = super(TciBatch, self).create(vals)
        ean = generate_ean(self.name)
        res.barcode = ean
        return res


    # Create merged attahments
    @api.multi
    def create_bach_report_pdf(self, final=False):
        # delete current records
        attach_ids = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id),
                                                       ('res_field', 'in', ['batch_report_document','batch_report_document_temp'])])
        if attach_ids:
            attach_ids.unlink()

        if final:
            if not self.external_ref:
                raise UserError(_("External Reference can not be empty to create the Batch Report"))
            elif not self.external_ref_file:
                raise UserError(_("Attach the external reference file to the Batch before to create the Batch Report"))
        # generate pdf name
        pdf_name = str(self.external_ref or 'Temporary_File') + str('-') + str('Batch-Report - ') + str(self.name) + str('.pdf')
        self.batch_report_name = pdf_name
        if not self.batch_report_document:
            new = False
        else:
            new = True
        # merger report
        decoded_data = []

        # add external ref file if exist
        if self.external_ref_file:
            decoded_data.append(self.external_ref_file)

        # add batch report
        pdf_report = self.env.ref('analytic_wbs_batch.tci_batch_report').sudo().render_qweb_pdf([self.id])[0]
        decoded_data.append(base64.b64encode(pdf_report or b''))

        # add all attachments
        attachment_ids = self.approval_report_ids
        for att in attachment_ids:
            decoded_data.append(att.datas)

        merged_pdf_report = pike_pdf_merge.process_from_stack(decoded_data)

        report = base64.b64encode(merged_pdf_report)

        if final:
            res_field = 'batch_report_document'
        else:
            res_field = 'batch_report_document_temp'

        ir_values = {
            'name': pdf_name,
            'type': 'binary',
            'datas': report,
            'res_model': self._name,
            'datas_fname': pdf_name,
            'res_id': self.id,
            'res_field': res_field,
            'mimetype': 'application/pdf',
        }
        self.env['ir.attachment'].create(ir_values)
        if final:
            if new:
                self.message_post(body="Document Review Report Created")
            else:
                self.message_post(body="Document Review Report Updated")

    def button_create_temp_batch_report(self):
        self.create_bach_report_pdf()

    def button_create_batch_report(self):
        self.create_bach_report_pdf(final=True)

    # Send email with merged attahments
    @api.multi
    def send_batch_report_by_email(self):
        '''
        This function opens a window to compose an email, with the Batch Processing report template message loaded by default
        '''

        self.ensure_one()

        # Remove Self Followers
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'tci.batch'),
            ('res_id', '=', self.id)])
        for follower in followers:
            follower.sudo().unlink()

        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env.ref('analytic_wbs_batch.email_template_tci_batch_approved')
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        # Get approval report
        report = self.env['ir.attachment'].search([('res_field', '=', 'batch_report_document'),
                                                   ('res_id', '=', self.id), ('res_model', '=', 'tci.batch')], order='create_date desc', limit=1)
        if template_id:
            if report:
                template_id.write({'attachment_ids': [(6, 0, [report.id])]})
            else:
                raise osv.except_osv(('Error'), ('Report not created, add function to create the report from the send by email buton Validate if we can create and send the new report'))
                self.create_merged_pdf()
                template_id.write({'attachment_ids': [(6, 0, [report.id])]})

        '''
        attachment_ids = []
        for att in self.attachment_ids:
            attachment_ids.append(att.id)
        template_id.write({'attachment_ids': [(6, 0, attachment_ids)]})
        '''
        ctx = {
            'default_model': 'tci.batch',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment',
        }
        if template_id:
            ctx_template = {
                'default_use_template': bool(template_id.id),
                'default_template_id': template_id.id,
            }
            ctx.update(ctx_template)

        '''
        # update send-out to vendor
        self.is_back_to_vendor = True
        self.back_to_vendor_date = datetime.now()
        '''

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def get_distribution_list(self):
        return str([user.id for user in self.po_id.tci_distribution_list]).replace('[', '').replace(']', '')


# Genration of barcode
def ean_checksum(eancode):
    """returns the checksum of an ean string of length 13, returns -1 if
    the string has the wrong length"""
    if len(eancode) != 13:
        return -1
    oddsum = 0
    evensum = 0
    eanvalue = eancode
    reversevalue = eanvalue[::-1]
    finalean = reversevalue[1:]

    for i in range(len(finalean)):
        if i % 2 == 0:
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
    total = (oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10.0)) % 10
    return check


def check_ean(eancode):
    """returns True if eancode is a valid ean13 string, or null"""
    if not eancode:
        return True
    if len(eancode) != 13:
        return False
    try:
        int(eancode)
    except:
        return False
    return ean_checksum(eancode) == int(eancode[-1])


def generate_ean(ean):
    """Creates and returns a valid ean13 from an invalid one"""
    if not ean:
        return "0000000000000"
    ean = re.sub("[A-Za-z]", "0", ean)
    ean = re.sub("[^0-9]", "", ean)
    ean = ean[:13]
    if len(ean) < 13:
        ean = ean + '0' * (13 - len(ean))
    return ean[:-1] + str(ean_checksum(ean))


class TciBatchType(models.Model):
    _name = 'tci.batch_type'
    _description = 'Tci Batch Type'
    _order = 'order desc'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)
    order = fields.Integer('Order', default=99)
    is_active = fields.Boolean('Active', default=False)

