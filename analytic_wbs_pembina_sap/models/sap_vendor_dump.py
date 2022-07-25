# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime

class wbs_sap_po_line_dump(models.Model):
    _name = 'sap.po_line_dump'
    _description = 'SAP PO Lines Dump'
    _order = 'document_date desc'

    # Data dump fields from SAP
    document_date = fields.Date('Document Date')
    created_on = fields.Date('Created on')
    purchasing_doc = fields.Char('Purchasing Document')
    sap_item = fields.Integer('Item')
    vendor = fields.Char('Vendor/supplying plant')
    short_text = fields.Char('Short Text')
    wbs_element = fields.Char('WBS Element')
    deletion_indicator = fields.Char('Deletion Indicator')
    seq_no_of_account_assgt = fields.Integer('Seq. No. of Account Assgt')
    order_quantity = fields.Float('Order Quantity')
    net_price = fields.Float('Net Price')
    net_order_value = fields.Float('Net Order Value')
    currency = fields.Char('Currency')
    distribution_pcent = fields.Float('Distribution (%)')

    qty_to_deliver = fields.Float('Still to be delivered (qty)')
    value_to_deliver = fields.Float('Still to be delivered (value)')
    qty_to_invoice = fields.Float('Still to be invoiced (qty)')
    value_to_invoice = fields.Float('Still to be invoiced (val.)')

    computed_uid = fields.Char(string='Computed UID', store=True, compute='_compute_uid')

    duplicate = fields.Boolean(string='Duplicate computed uid', store=True)

    mapped = fields.Boolean(default=False, string='Mapped')
    po_line_map_id = fields.Many2one('sap.po_line_mapped', 'Mapped Actual')

    @api.depends('purchasing_doc', 'sap_item', 'seq_no_of_account_assgt')
    def _compute_uid(self):
        for record in self:
            str1 = str(record.purchasing_doc)
            str2 = str(record.sap_item)
            str3 = str(record.seq_no_of_account_assgt)
            separator = str(".")
            record.computed_uid = str1 + separator + str2 + separator + str3


class wbs_sap_po_line_mapped(models.Model):

    _name = 'sap.po_line_mapped'
    _description = 'SAP PO Lines Mapped'
    _order = 'document_date desc'

    sap_import_id = fields.Many2one('sap.import', string='SAP Import')
    last_change_sap_import_id = fields.Many2one('sap.import', string='SAP Import Last Change')
    changed_fields = fields.Char(string='Changed Fields')

    document_date = fields.Date('Document Date')
    created_on = fields.Date('Created on')
    purchasing_doc = fields.Char('Purchasing Document')
    sap_item = fields.Integer('Item')
    vendor = fields.Char('Vendor/supplying plant')
    short_text = fields.Char('Short Text')
    wbs_element = fields.Char('WBS Element')
    deletion_indicator = fields.Char('Deletion Indicator')
    seq_no_of_account_assgt = fields.Integer('Seq. No. of Account Assgt')

    computed_uid = fields.Char(string='Computed UID')

    _sql_constraints = [
        ('uid_uniq', 'unique (computed_uid)', "Tag computed_uid already exists !"),
    ]

    account_id = fields.Many2one('account.analytic_wbs.account', 'Account wbs', required=False, ondelete='restrict')
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=False, ondelete='restrict')
    project_id = fields.Many2one('project.project', string='Project', required=False, ondelete='restrict')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=False, ondelete='restrict')
    purchase_order_id = fields.Many2one('purchase.order', string='PO', required=False, ondelete='restrict')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='PO Line', required=False, ondelete='restrict')

    order_quantity = fields.Float('Order Quantity')
    net_price = fields.Float('Net Price')
    net_order_value = fields.Float('Net Order Value')

    currency = fields.Char('Currency')

    distribution_pcent = fields.Float('Distribution (%)')

    qty_to_deliver = fields.Float('Still to be delivered (qty)')
    value_to_deliver = fields.Float('Still to be delivered (value)')
    qty_to_invoice = fields.Float('Still to be invoiced (qty)')
    value_to_invoice = fields.Float('Still to be invoiced (val.)')

    @api.multi
    def get_vendor_sap_code(self):
        # this function will extract the vendor code and the vendor name from the vendor string in SAP
        if not self.vendor:
            raise Warning(
                'Empty Vendor/supplying plant in Vendor Table. All records must be linked to a vendor')
        if self.vendor:
            res = {
                'code': self.vendor[:6],
                'name': self.vendor[11:],
            }
            return res

    @api.multi
    def get_vendor_info(self):
        code = self.get_vendor_sap_code()['code']
        name = self.get_vendor_sap_code()['name']
        vendor_id = self.env['res.partner'].get_partner_from_sap_code(code)
        if vendor_id:
            vname = vendor_id.name
            if not vname == name:
                # todo:
                print('test')
                #raise Warning('create function to message pop up to display the current vendor name and ask if user wants to change it')
        if not vendor_id:
            # create the new vendor
            vendor_id = self.env['res.partner'].create_new_vendor(code, name)

        return vendor_id

    @api.multi
    def get_purchase_order_info(self):
        code = self.purchasing_doc
        vendor = self.vendor_id

        if not vendor:
            vendor = self.get_vendor_info()
        po_id = self.env['purchase.order'].get_po_from_sap_code(code)
        if vendor and not po_id:
            # Find po creation date
            doc_date = self.env['sap.po_line_mapped'].search([('purchasing_doc', '=', code)],
                                                             order='document_date asc', limit=1).document_date
            # transform date to datetime
            date_order = datetime(doc_date.year, doc_date.month, doc_date.day)
            # create the new purchasse order for the vendor
            po_id = self.env['purchase.order'].create_new_po(code, vendor, date_order)
            # Todo: Add tag to PO for creation of forecast later *** PRIORITY 1
        return po_id

    @api.multi
    def get_purchase_order_line_info(self):
        map_uid = self.computed_uid
        # Validate if the line exist already using the computed UID
        # todo: verify if this validation is required or if this is redondant
        po_line = self.env['purchase.order.line'].search([('sap_line_mapped', '=', map_uid)])
        if po_line:
            # validate the data mapped to see if it has changed
            print('create function to validate information from the mapped po'
                  'the mapped_uid is already linked to a po_line in the database'
                  'in theory, the only way to get here is if a mapped po_line has been deleted from the dump')
            # elements to validate for changes: short text, wbs element, deletion indicator,

        if not po_line:
            # Create the new po line
            for record in self:
                po_line = self.env['purchase.order.line'].create_new_po_line_from_sap(record)

        return po_line
