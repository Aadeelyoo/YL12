# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WorkflowInvoiceDump(models.Model):
    _name = 'workflow.invoice_dump'
    _description = 'Workflow invoice Lines Dump'
    _order = 'workflow_item desc'

    # Data dump fields from WORKFLOW
    sort_order = fields.Char('Sort Order')
    workflow_item = fields.Integer('VIM ID')
    current_step = fields.Char('Current Step')
    status = fields.Char('Status')
    current_user = fields.Char('Current User')
    vendor_no = fields.Integer('Vendor No')
    vendor_name = fields.Char('Vendor Name')
    invoice_no = fields.Char('Invoice No')
    invoice_amount = fields.Float(string='Invoice Amount')
    invoice_date = fields.Datetime('Invoice Date')
    scan_date = fields.Datetime('Scan Date')
    po_no = fields.Char('PO No')
    invoice_url = fields.Char('FileNet URL')
    admin_url = fields.Char('Alt URL')
    comment_url = fields.Char('Comment URL')
    history_url = fields.Char('History URL')
    bpm_url = fields.Char('BPM URL')
    payment_no = fields.Char('Payment No')
    doc_type = fields.Char('Document Type')

    computed_uid = fields.Char(string='Computed UID', store=True, compute='_compute_uid')
    duplicate = fields.Boolean(string='Duplicate computed uid', store=True)

    mapped = fields.Boolean(default=False, string='Mapped')
    workflow_invoice_map_id = fields.Many2one('workflow.invoice_mapped', 'Mapped Workflow Invoice')

    @api.depends('workflow_item', 'po_no')
    def _compute_uid(self):
        for record in self:
            str1 = str('vim_') + str(record.workflow_item)
            separator = str(".")
            record.computed_uid = str1


class WorkflowInvoiceMapped(models.Model):
    _name = 'workflow.invoice_mapped'
    _description = 'Workflow invoice Mapped'
    _order = 'workflow_item desc'

    workflow_import_id = fields.Many2one('workflow.import', string='Workflow Import')
    last_change_workflow_import_id = fields.Many2one('workflow.import', string='Workflow Import Last Change')
    changed_fields = fields.Char(string='Changed Fields')

    sort_order = fields.Char('Sort Order')
    workflow_item = fields.Integer('VIM ID')
    current_step = fields.Char('Current Step')
    status = fields.Char('Status')
    current_user = fields.Char('Current User')
    vendor_no = fields.Integer('Vendor No')
    vendor_name = fields.Char('Vendor Name')
    invoice_no = fields.Char('Invoice No')
    invoice_amount = fields.Float(string='Invoice Amount')
    invoice_date = fields.Date('Invoice Date')
    scan_date = fields.Date('Scan Date')
    po_no = fields.Char('PO No')
    invoice_url = fields.Char('FileNet URL')
    admin_url = fields.Char('Alt URL')
    comment_url = fields.Char('Comment URL')
    history_url = fields.Char('History URL')
    bpm_url = fields.Char('BPM URL')
    payment_no = fields.Char('Payment No')
    doc_type = fields.Char('Document Type')

    computed_uid = fields.Char(string='WORKFLOW Computed UID')

    _sql_constraints = [
        ('uid_uniq', 'unique (computed_uid)', "Tag computed_uid already exists !"),
    ]

    purchase_order_id = fields.Many2one('purchase.order', string='PO', required=False, ondelete='restrict')

    tci_id = fields.Many2one('tci', 'Cost Item No', required=False)

    @api.multi
    def update_po_id(self):
        for record in self:
            if record.po_no and not record.purchase_order_id:
                po = self.env['purchase.order'].search([('internal_ref', '=', record.po_no)], limit=1)
                if po:
                    record.purchase_order_id = po.id
