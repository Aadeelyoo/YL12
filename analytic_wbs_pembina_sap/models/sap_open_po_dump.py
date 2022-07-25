# -*- coding: utf-8 -*-

from odoo import models, fields, api


class wbs_sap_open_po_line_dump(models.Model):
    _name = 'sap.open_po_line_dump'
    _description = 'SAP Open Commitment Lines Dump'
    _order = 'document_date desc'

    # Data dump fields from SAP
    document_date = fields.Date('Document Date')
    ref_document_number = fields.Char('Ref Document Number')
    reference_item = fields.Integer('Reference Item')
    sap_name = fields.Char('Name')
    val_ca_area_crcy = fields.Float(string='Val/COArea Crcy')
    project_definition = fields.Char('Project Definition')
    wbs_element = fields.Char('WBS Element')
    deletion_indicator = fields.Char('Deletion Indicator')
    vendor_no = fields.Integer('Vendor')
    deadline_item = fields.Integer('Deadline Item')
    debit_date = fields.Date('Debit Date')

    computed_uid = fields.Char(string='Computed UID', store=True, compute='_compute_uid')
    #sap_line_mapped = fields.Char(string='Computed SAP PO line UID', store=True, compute='_compute_uid')

    #duplicate = fields.Boolean(string='Duplicate computed uid', store=True)

    #mapped = fields.Boolean(default=False, string='Mapped')
    #open_po_map_id = fields.Many2one('sap.open_po_line_mapped', 'Mapped Open Commitment')

    @api.depends('ref_document_number', 'reference_item')
    def _compute_uid(self):
        for record in self:
            str1 = str(record.ref_document_number)
            str2 = str(record.reference_item)
            str3 = str(record.deadline_item)
            str4 = str(record.wbs_element)
            separator = str(".")
            record.computed_uid = str1 + separator + str2 + separator + str3 + separator + str4
            #record.sap_line_mapped = str1 + separator + str2


class wbs_sap_open_po_line_mapped(models.Model):
    _name = 'sap.open_po_line_mapped'
    _description = 'SAP Open Commitment Lines Mapped'
    _order = 'document_date desc'

    sap_import_id = fields.Many2one('sap.import', string='SAP Import')

    document_date = fields.Date('Document Date')
    ref_document_number = fields.Char('Ref Document Number')
    reference_item = fields.Integer('Reference Item')
    sap_name = fields.Char('Name')
    val_ca_area_crcy = fields.Float(string='Val/COArea Crcy')
    project_definition = fields.Char('Project Definition')
    wbs_element = fields.Char('WBS Element')
    deletion_indicator = fields.Char('Deletion Indicator')
    vendor_no = fields.Integer('Vendor')
    deadline_item = fields.Integer('Deadline Item')
    debit_date = fields.Date('Debit Date')

    computed_uid = fields.Char(string='SAP Computed UID')
    #sap_line_mapped = fields.Char(string='Computed SAP PO line UID')

    account_id = fields.Many2one('account.analytic_wbs.account', 'Account wbs', required=False, ondelete='restrict')
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=False, ondelete='restrict')
    project_id = fields.Many2one('project.project', string='Project', required=False)
    purchase_order_id = fields.Many2one('purchase.order', string='PO', required=False, ondelete='restrict')

    tci_id = fields.Many2one('tci', string='TCI', related='tci_line_id.tci_id')
    tci_line_id = fields.Many2one('tci.line', string='TCI')

    @api.multi
    def update_po_id(self):
        for record in self:
            if record.ref_document_number and not record.purchase_order_id:
                po = self.env['purchase.order'].search([('internal_ref', '=', record.ref_document_number)], limit=1)
                if po:
                    record.purchase_order_id = po.id

    @api.multi
    def update_account_project(self):
        for record in self:
            if record.wbs_element and not record.account_project_id:
                project_wbs = self.env['account.analytic_wbs.project'].search([('name', '=', record.wbs_element)], limit=1)
                if project_wbs:
                    vals = {
                        'account_project_id': project_wbs.id,
                        'project_id': project_wbs.project_id.id,
                        'account_id': project_wbs.account_id.id,
                    }
                    record.write(vals)

    @api.multi
    def create_new_tci_line(self, tci_id):
        for rec in self:
            descr = str(rec.sap_name) + str(' - ') + str(rec.computed_uid)
            new_line = {
                'name': rec.computed_uid,
                'description': descr,
                'quantity': 1,
                'unit_amount': rec.val_ca_area_crcy,
                'analytic_project_id': rec.account_project_id.id,
                'tci_id': tci_id,
                'date': rec.debit_date,
            }

            new_line_rec = self.env['tci.line'].create(new_line)
            rec.tci_line_id = new_line_rec.id
        return True