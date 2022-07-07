# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TciBatch(models.Model):
    _inherit = "tci"

    batch_id = fields.Many2one('tci.batch', 'Batch', required=False, ondelete='restrict', copy=False)
    external_ref = fields.Char('External Reference', related="batch_id.external_ref")

    @api.multi
    def ir_action_create_batch_summary(self):

        lem_ids = []
        lem_name = []
        seen_batch_ids = set()
        seen_po_ids = set()
        for rec in self:
            lem_ids.append(rec['id'])
            lem_name.append(rec['name'])
            po_id = rec['po_id']
            batch_id = rec['batch_id']

            if po_id not in seen_po_ids:
                seen_po_ids.add(po_id)
            if batch_id not in seen_batch_ids:
                seen_batch_ids.add(batch_id)
            if not rec.approval_report_id:
                raise UserError(
                    _('LEM # %s status report is not created. Please create the Status Report Prior to create the batch') % rec.name)

        po_ids = list(seen_po_ids)[0]
        batch_ids = list(seen_batch_ids)[0]

        if batch_ids:
            raise UserError(_('The following LEMs are already included in a Batch Summary. %s Lems can only be assigned to 1 Batch') % lem_name)

        if len(po_ids) > 1:
            raise UserError(_('The LEMs selected are linked to more than 1 PO. Only LEMs from unique PO can be assigned to the same Batch'))

        vals = {
            'po_id': po_ids[0].id,
            'partner_id': po_ids[0].partner_id.id,
        }

        new_batch = self.env['tci.batch'].create(vals)
        new_batch.tci_ids = lem_ids

    @api.depends('mail_approval_state', 'po_id', 'partner_id',
                 'parent_invoice_act_rel_id', 'po_rev', 'parent_invoice_wt_rel_id',
                 'mail_approval_start_date', 'is_void', 'tci_type', 'child_invoice_act_rel_ids',
                 'batch_id.state')
    def _compute_state(self):
        for tci in self:
            if tci.is_superuser_state:
                state = 'superuser_overwrite'

            else:
                if tci.tci_type in ('wt', 'cr', 'estimate'):
                    if tci.parent_invoice_wt_rel_id:
                        state = 'invoiced'

                    elif tci.batch_id.state in ('approved', 'posted'):
                        state = 'completed'

                    elif tci.is_void:
                        state = 'void'

                    elif tci.po_rev:
                        state = 'released'

                    elif not tci.po_id or not tci.partner_id:
                        state = "new"

                    elif tci.po_id and tci.partner_id and not tci.mail_approval_state:
                        state = "draft"

                    elif tci.po_id and tci.partner_id and tci.mail_approval_state in ('new', 'stop'):
                        state = "draft"

                    elif tci.mail_approval_state in ('review', 'hold'):
                        state = 'review'

                    elif tci.mail_approval_state in ('approved', 'rejected'):
                        state = tci.mail_approval_state
                    else:
                        print('Need to update state function for this else never to happen')

                elif tci.tci_type == 'maccr':
                    if tci.is_void:
                        state = 'void'
                    else:
                        state = 'new'

                elif tci.tci_type == 'ocommit':
                    state = 'new'

                elif tci.tci_type == 'inv':
                    if tci.invoice_id:
                        state = 'invoiced'

                    elif tci.is_void:
                        state = 'void'

                    elif tci.child_invoice_act_rel_ids:
                        state = 'completed'
                    else:
                        state = 'new'

                elif tci.tci_type == 'act':
                    if tci.parent_invoice_act_rel_id_no_link or tci.parent_invoice_act_rel_id:
                        state = 'mapped'
                    else:
                        state = 'new'

            if not tci.state == state:
                tci.state = state
