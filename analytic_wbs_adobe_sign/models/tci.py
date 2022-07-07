from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import pike_pdf_merge, adobesign

import base64

class Tci(models.Model):
    _inherit = "tci"

    adobe_control_flag = fields.Boolean(copy=False)
    controlled_by_adobe_sign = fields.Boolean(compute="_check_adobe_control")
    adobe_agreement_status = fields.Char("Agreement Status", copy=False)

    @api.multi
    def _check_adobe_control(self):
        for rec in self:
            user_env = self.env.user.company_id
            if user_env.activate_adobe_sign and user_env.adobe_sign_account_id and rec.adobe_control_flag:
                rec.controlled_by_adobe_sign = True
            else:
                rec.controlled_by_adobe_sign = False

    # def test_pdf_generation(self):
    #     pdf_report = self.env.ref('analytic_wbs.report_for_solevo_tci_reportt').sudo().with_context(adobe_sign=True, display="none").render_qweb_pdf([self.id])[0]
    #     import time
    #     import os
    #     dir_path = os.path.dirname(os.path.realpath(__file__))
    #     ts = str(time.time())
    #     # with open(os.path.join(dir_path, "signed-" + ts + ".pdf"), 'w') as f:
    #     #     f.write(new_request.content)
    #     open(os.path.join(dir_path, "signed-" + ts + ".pdf"), 'wb').write(pdf_report)
    #
    #     # decoded_data.append(pdf_report)
    #     # atts = self.approval_document_ids.mapped('datas')
    #     # atts.insert(0, base64.b64encode(pdf_report or b''))
    #     # merged_pdf = pike_pdf_merge.process_from_stack(atts)
    #     # return base64.b64encode(merged_pdf)

    def get_merged_pdf_for_approval(self):
        if not self.batch_id or self.batch_id.state == 'draft':
            decoded_data = []
            pdf_report = self.env.ref('analytic_wbs.report_for_solevo_tci_reportt').sudo().with_context(adobe_sign=True, display="none").render_qweb_pdf([self.id])[0]

            decoded_data.append(pdf_report)
            atts = self.approval_document_ids.mapped('datas')
            atts.insert(0, base64.b64encode(pdf_report or b''))
            merged_pdf = pike_pdf_merge.process_from_stack(atts)
            return base64.b64encode(merged_pdf)

    def get_signer_sequence(self, signer):
        mail_stack = {}
        templ_list = []
        counter = 1
        for approver in self.mail_user_ids:
            if approver.email not in templ_list:
                mail_stack[approver.email] = counter
                counter += 1

            templ_list.append(approver.email)
        return mail_stack[signer]

    @api.multi
    def write(self, vals):
        if self.env.user.company_id.activate_adobe_sign and self.env.user.company_id.adobe_sign_account_id:
            if 'mail_approval_state' in vals:
                # if not vals.get('mail_approval_state'):
                #     self.write({
                #         "adobe_agreement_id": False,
                #         "agreement_status": False
                #     })
                if vals.get('mail_approval_state') == 'review':
                    if self.approval_document_ids and self.mail_user_ids:
                        pdf_name = _('Document Review Report - {} - {}.pdf').format(self.reference, self.name)
                        pdf = self.get_merged_pdf_for_approval()
                        document = {
                            "name": pdf_name,
                            "data" : pdf,
                        }
                        signers = self.mail_user_ids.filtered(lambda u : u.email)
                        self.env['adobe.agreement'].start_adobe_document_sign_process(
                            document=document, signers=signers, res_model=self._name, res_id=self.id,
                            destination_field="approval_report_id"
                        )
            if 'adobe_agreement_status' in vals:
                if vals.get('adobe_agreement_status') == 'CANCELLED' and self.adobe_agreement_status != 'CANCELLED':
                    self.send_rejection_email_to_distribution()
        return super(Tci, self).write(vals)

    @api.model
    def create(self, vals):
        user_env = self.env.user.company_id
        adobe_activated = user_env.activate_adobe_sign if user_env.adobe_sign_account_id else False

        if adobe_activated:
            vals['adobe_control_flag'] = True

        return super(Tci, self).create(vals)

    def send_rejection_email_to_distribution(self):
        if self.po_id:
            if self.po_id.tci_distribution_list:
                template = self.env.ref('analytic_wbs.email_template_tci_approved')
                template.sudo().send_mail(self.id, force_send=True)

    def approve_related_document(self):
        self.ensure_one()
        self.action_tci_approve()

    def reject_related_document(self, feedback=False):
        self.ensure_one()
        self.action_tci_reject(feedback)