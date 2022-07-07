import logging
import os
import datetime
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from odoo.tools import adobesign
    _adobe_sign_module_imported = True
except ImportError:
    _adobe_sign_module_imported = False
    _logger.info(
        "The `adobesign_odoo` module is not available. "
    )


class AdobeAgreement(models.Model):
    _name = "adobe.agreement"
    _description = 'Adobe Agreements'
    _rec_name = 'name'

    name = fields.Char('Name')
    agreement_id = fields.Char("Agreement ID")
    agreement_status = fields.Char(string="Status")
    res_model = fields.Char(
        'Related Document Model Name', index=True)
    res_id = fields.Integer(
        'Related Document ID', index=True, help='Id of the resource related model')
    destination_field = fields.Char(
        'Related Document Model Field', index=True)
    unsigned_agreement = fields.Binary(attachment=True, string='Unsigned Document')
    signed_agreement = fields.Binary(attachment=True, string='Signed Document')
    agreement_event_ids = fields.One2many('adobe.agreement.events', 'agreement_id')
    eligible_cancellation = fields.Boolean('Allow Cancellation', compute='_check_cancellation_eligibility')

    @api.multi
    def write(self, vals):
        if 'agreement_status' in vals:
            res = super(AdobeAgreement, self).write(vals)
            if self.res_model and self.res_id:
                object_rel = self.env[self.res_model].browse(self.res_id)
                if object_rel:
                    object_rel.write({
                        "adobe_agreement_status": vals.get('agreement_status')
                    })
        else:
            res = super(AdobeAgreement, self).write(vals)

        return res

    @api.multi
    def _check_cancellation_eligibility(self):
        for rec in self:
            if rec.agreement_event_ids.mapped('event_type') not in ['ACTION_COMPLETED'] and rec.agreement_status == 'OUT_FOR_SIGNATURE':
                rec.eligible_cancellation = True
            else:
                rec.eligible_cancellation = False

    def start_adobe_document_sign_process(self, document, signers, res_model, res_id, destination_field=False):

        account_id = self.env.user.company_id.adobe_sign_account_id
        if document and account_id and signers and res_model and res_id:
            token_obj = account_id

            access_token = token_obj.access_token
            expire_in = token_obj.expire_in
            client_id = token_obj.client_id
            client_secret = token_obj.client_secret
            api_access_point = token_obj.adobesign_domain
            refresh_token = token_obj.refresh_token
            redirect_url = token_obj.redirect_url

            if access_token :
                token = adobesign.verify_token(access_token, redirect_url, expire_in, api_access_point,
                                               client_id,
                                               client_secret, refresh_token)
                if not token :
                    raise UserError(_('Error in refreshing token'))
                else :
                    access_token = token
                    token_obj.access_token = access_token
                    token_obj.access_token_time = datetime.datetime.now()
            else :
                raise UserError(_('Please Generate Access Token'))

            file_path = adobesign.get_file_path2(document['data'], document['name'])

            transient_doc_id = adobesign.upload_document(api_access_point, file_path, access_token)
            # content_encoded = adobesign.read_file(file_path)
            os.remove(file_path)


            agreement = adobesign.send_agreement_multiple(api_access_point, access_token, transient_doc_id, signers, document['name'])
            if 'Access token' in str(agreement[1]):
                raise UserError(_(str(agreement[1])))
            if 'unable to process your PDF document' in str(agreement[1]):
                raise UserError(_(str(agreement[1])))
            agreement_id = agreement[1]

            existing_agreements = self.search([('res_model', '=', res_model), ('res_id', '=', res_id)])

            if existing_agreements:
                for existing in existing_agreements:
                    existing.unlink()

            self_agreement = self.create({
                "name": document['name'],
                "agreement_id" : agreement_id,
                "destination_field": destination_field,
                "agreement_status" : "OUT_FOR_SIGNATURE",
                "res_model" : res_model,
                "res_id": res_id,
            })
            # self.env.cr.commit()
            ir_values = {
                'name': document['name'],
                'type': 'binary',
                'datas': document['data'],
                'res_model': self._name,
                'datas_fname': document['name'],
                'res_id': self_agreement.id,
                'res_field': 'unsigned_agreement',
                'mimetype': 'application/pdf',
            }
            attachment = self.env['ir.attachment'].create(ir_values)
            # self_agreement.unsigned_agreement = attachment.id

    @api.multi
    def cron_process_adobe_sign_docs(self, process_all=True):
        if self.env.user.company_id.activate_adobe_sign and self.env.user.company_id.adobe_sign_account_id:
            account_id = self.env.user.company_id.adobe_sign_account_id

            if process_all:
                agreements = self.search([('agreement_status', '!=', 'SIGNED')])
            else:
                agreements = self

            if not account_id:
                return
            if not agreements:
                return
            token_obj = account_id
            access_token = token_obj.access_token
            api_access_point = token_obj.adobesign_domain
            expire_in = token_obj.expire_in
            client_id = token_obj.client_id
            client_secret = token_obj.client_secret
            refresh_token = token_obj.refresh_token
            redirect_url = token_obj.redirect_url

            if access_token:
                token = adobesign.verify_token(access_token, redirect_url, expire_in, api_access_point, client_id,
                                               client_secret, refresh_token)
                if not token:
                    raise UserError(_('Error in refreshing token'))
                else:
                    access_token = token
                    token_obj.access_token = access_token
                    token_obj.access_token_time = datetime.datetime.now()
            else:
                raise UserError(_('Please Generate Access Token'))

            for agreement in agreements:
                agreement_id = agreement.agreement_id

                if agreement.agreement_status != 'SIGNED':
                    # Process Agreement
                    agreement_events = adobesign.get_agreement_events(api_access_point, access_token, agreement_id)
                    if agreement_events:
                        exiting_events = agreement.agreement_event_ids.mapped('event_id')
                        comments_to_record = ['REJECTED', 'DELEGATE', 'SHARE']
                        for event in agreement_events :
                            if event['id'] not in exiting_events:
                                agreement.sudo().write({
                                    "agreement_event_ids": [(0, 0, {
                                        "event_id" : event['id'],
                                        "event_type" : event['type'],
                                        "agreement_id" : agreement_id,
                                        "description" : event['description'] if event['type'] != 'CREATED' else False,
                                        "comment" : event['comment'] if event['type'] in comments_to_record else False,
                                        "date" : event['date'].replace('T', ' ')[:19]
                                    })]
                                })

                                target_object = self.env[agreement.res_model].browse(agreement.res_id)
                                for approver in target_object.mail_user_ids:
                                    if approver.email == event['participantEmail'] :
                                        if event['type'] == 'ACTION_COMPLETED':
                                            # self.env[agreement.res_model].browse(agreement.res_id)
                                            target_object.sudo(approver.id).approve_related_document()

                                        if event['type'] == 'REJECTED' :
                                            target_object.sudo(approver.id).reject_related_document(feedback=event['comment'])

                                        self.env.cr.commit()


                    # Download Agreement
                    status_array = adobesign.get_agreement_detail(api_access_point, access_token, agreement_id)
                    if status_array:
                        status = status_array[0]

                        if status == 'SIGNED':
                            filename = status_array[1]
                            response_content = adobesign.download_agreement(api_access_point, access_token, agreement_id)
                            if response_content:
                                encoded_string = base64.b64encode(response_content)

                                try:
                                    filename = str(filename).split(']')[1]
                                except:
                                    pass

                                query = [('res_model', '=', agreement.res_model), ('res_id', '=', agreement.res_id)]

                                if agreement.destination_field:
                                    query += [('res_field', '=', agreement.destination_field)]

                                attach_ids = self.env['ir.attachment'].search(query)

                                if attach_ids:
                                    for att in attach_ids:
                                        att.write({
                                            "datas": encoded_string
                                        })

                                ir_values = {
                                    'name' : agreement.name,
                                    'type' : 'binary',
                                    'datas' : encoded_string,
                                    'res_model' : self._name,
                                    'datas_fname' : agreement.name,
                                    'res_id' : agreement.id,
                                    'res_field' : 'signed_agreement',
                                    'mimetype' : 'application/pdf',
                                }
                                self.env['ir.attachment'].create(ir_values)

                            else:
                                raise UserError(_('Error in downloading file'))

                        agreement.agreement_status = status

    def refresh_agreement(self):
        self.cron_process_adobe_sign_docs(process_all=False)

    def cancel_agreement(self):
        self.ensure_one()

        if self.eligible_cancellation:

            account_id = self.env.user.company_id.adobe_sign_account_id
            if account_id:
                token_obj = account_id

                access_token = token_obj.access_token
                expire_in = token_obj.expire_in
                client_id = token_obj.client_id
                client_secret = token_obj.client_secret
                api_access_point = token_obj.adobesign_domain
                refresh_token = token_obj.refresh_token
                redirect_url = token_obj.redirect_url

                if access_token:
                    token = adobesign.verify_token(access_token, redirect_url, expire_in, api_access_point,
                                                   client_id,
                                                   client_secret, refresh_token)
                    if not token:
                        raise UserError(_('Error in refreshing token'))
                    else:
                        access_token = token
                        token_obj.access_token = access_token
                        token_obj.access_token_time = datetime.datetime.now()
                else:
                    raise UserError(_('Please Generate Access Token'))
                adobesign.cancel_agreement(api_access_point, access_token, self.agreement_id)
                self.refresh_agreement()
        else:
            raise UserError(_("Unable to cancel. Agreement is already signed by approver."))

    def acquire_agreement_information(self, res_id=False, res_model=False):
        agreement_view_id = self.env.ref('approval_mixin.adobe_agreement_semi_form_view').id
        if not res_id or not res_model:
            events_count = 0
            agreement_id = 0
        else:
            agreement = self.search([('res_id','=',res_id),('res_model','=',res_model)], limit=1)
            agreement_id = agreement.id
            events_count = len(agreement.agreement_event_ids.ids)
        vals = {
            'events_count': events_count,
            'agreement_id': agreement_id,
            'agreement_view_id': agreement_view_id,
        }
        return vals

class AdobeAgreementEvents(models.Model):
    _name = "adobe.agreement.events"

    agreement_id = fields.Many2one("adobe.agreement", string='Adobe Agreement',
        index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
        help="Adobe agreement generated events.")
    event_id = fields.Char("ID")
    date = fields.Datetime("Date")
    description = fields.Char("Description")
    event_type = fields.Char("Type")
    comment = fields.Char("Comment")