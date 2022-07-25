# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class wbs_sap_actuals_line_dump(models.Model):
    _name = 'sap.actuals_line_dump'
    _description = 'SAP Actuals Lines Dump'
    _order = 'document_date desc'

    # Data dump fields from SAP
    document_date = fields.Date('Document Date')
    posting_date = fields.Date('Posting Date')
    document_number = fields.Char('Document Number')
    ref_document_number = fields.Char('Ref Document Number')
    object = fields.Char('Object')
    purchasing_document = fields.Char('Purchasing Document')
    sap_item = fields.Integer('Item')
    vendor_name = fields.Char('Vendor Name')
    name_of_employee_or_applicant = fields.Char('Name of Employee or Applicant')
    cost_element_descr = fields.Char('Cost element descr.')
    name_of_offseting_account = fields.Char('Name of offsetting account')
    val_ca_area_crcy = fields.Float(string='Val/COArea Crcy')
    transaction_currency = fields.Char('Transaction Currency')
    total_quantity = fields.Float(string='Total quantity')
    document_header_text = fields.Char('Document Header Text')
    project_definition = fields.Char('Project Definition')
    fi_posting_item = fields.Integer('FI Posting Item')
    wbs_element = fields.Char('WBS Element')
    posting_now = fields.Integer('Posting now')
    recovery_indicator = fields.Char('Recovery Indicator')

    computed_uid = fields.Char(string='Computed UID', store=True, compute='_compute_uid')
    duplicate = fields.Boolean(string='Duplicate computed uid', store=True)

    mapped = fields.Boolean(default=False, string='Mapped')
    actual_map_id = fields.Many2one('sap.actuals_line_mapped', 'Mapped Actual')

    @api.depends('document_number', 'fi_posting_item', 'posting_now')
    def _compute_uid(self):
        for record in self:
            str1 = str(record.document_number)
            str2 = str(record.fi_posting_item)
            str3 = str(record.posting_now)
            str4 = str(record.cost_element_descr)
            str5 = str(record.val_ca_area_crcy)
            separator = str(".")
            record.computed_uid = str1 + separator + str2 + separator + str3 + separator + str4 + separator + str5

    @api.multi
    def tag_actuals(self):
        act_docs_dump = []
        dump_sum = 0
        for rec in self.env['sap.actuals_line_dump'].search([]):
            dump_sum = dump_sum + rec.val_ca_area_crcy
            if rec.document_number not in act_docs_dump:
                act_docs_dump.append(rec.document_number)
        print(act_docs_dump)
        print('Len dump = %s' % len(act_docs_dump))
        print('Sum dump = %s' % dump_sum)

        actuals = []
        act_sum = 0

        for rec in self.env['tci'].search([('tci_type', '=', 'act')]):
            act_sum = act_sum + rec.total_amount

            if rec.reference not in act_docs_dump:
                actuals.append(rec.reference)

        print(actuals)
        print('Len actuals = %s' % len(actuals))

class wbs_sap_actuals_line_mapped(models.Model):
    _name = 'sap.actuals_line_mapped'
    _description = 'SAP Actuals Lines Mapped'
    _order = 'document_date desc'

    sap_import_id = fields.Many2one('sap.import', string='SAP Import')

    document_date = fields.Date('Document Date')
    posting_date = fields.Date('Posting Date')
    document_number = fields.Char('Document Number')
    ref_document_number = fields.Char('Ref Document Number')
    object = fields.Char('Object')
    purchasing_document = fields.Char('Purchasing Document')
    sap_item = fields.Integer('Item')
    vendor_name = fields.Char('Vendor Name')
    name_of_employee_or_applicant = fields.Char('Name of Employee or Applicant')
    cost_element_descr = fields.Char('Cost element descr.')
    name_of_offseting_account = fields.Char('Name of offsetting account')
    val_ca_area_crcy = fields.Float(string='Val/COArea Crcy')
    transaction_currency = fields.Char('Transaction Currency')
    total_quantity = fields.Float(string='Total quantity')
    document_header_text = fields.Char('Document Header Text')
    project_definition = fields.Char('Project Definition')
    fi_posting_item = fields.Integer('FI Posting Item')
    wbs_element = fields.Char('WBS Element')
    posting_now = fields.Integer('Posting now')
    recovery_indicator = fields.Char('Recovery Indicator')

    computed_uid = fields.Char(string='SAP Computed UID')

    _sql_constraints = [
        ('uid_uniq', 'unique (computed_uid)', "Tag computed_uid already exists!"),
    ]

    account_id = fields.Many2one('account.analytic_wbs.account', 'Account wbs', required=False, ondelete='restrict')
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=False, ondelete='restrict')
    project_id = fields.Many2one('project.project', string='Project', required=False)
    purchase_order_id = fields.Many2one('purchase.order', string='PO', required=False, ondelete='restrict')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='PO Line', required=False, ondelete='restrict')

    tci_id = fields.Many2one('tci', string='TCI', related='tci_line_id.tci_id')
    tci_line_id = fields.Many2one('tci.line', string='TCI Line')

    employee_id = fields.Many2one('hr.employee', string='Employee', required=False, readonly=False)
    comment = fields.Char('Comment')


    @api.multi
    def update_po_id(self):
        for record in self:
            if record.purchasing_document and not record.purchase_order_id:
                po = self.env['purchase.order'].search([('internal_ref', '=', record.purchasing_document)], limit=1)
                if po:
                    record.purchase_order_id = po.id
                if not po:
                    # search for partner
                    partner_obj = self.env['res.partner']
                    purchase_obj = self.env['purchase.order']
                    vendor_id = partner_obj.search([('name', '=', record.vendor_name)], limit=1)
                    if not vendor_id:
                        # create vendor
                        val = {
                            'name': record.vendor_name,
                            'company_type': 'company'
                        }
                        vendor_id = partner_obj.create(val)
                    # Create PO
                    pval = {
                        'partner_id': vendor_id.id,
                        'internal_ref': record.purchasing_document,
                    }
                    new_po_id = purchase_obj.create(pval)
                    record.purchase_order_id = new_po_id.id
    @api.multi
    def update_employee_id(self):
        for record in self:
            if record.name_of_employee_or_applicant and not record.employee_id:
                employee_id = self.env['hr.employee'].get_employee_id_from_name(record.name_of_employee_or_applicant)
                if employee_id:
                    record.employee_id = employee_id.id

    @api.multi
    def create_new_tci_line(self, tci_id):
        for rec in self:
            descr = rec.document_header_text or rec.name_of_employee_or_applicant
            quantity = 1
            unit_amount = rec.val_ca_area_crcy

            # calculate unit rate and quantity for employee
            if rec.employee_id:
                if not rec.total_quantity == 0:
                    unit_amount = rec.val_ca_area_crcy / rec.total_quantity
                quantity = rec.total_quantity

            new_line = {
                'name': rec.computed_uid,
                'description': descr,
                'quantity': quantity,
                'unit_amount': unit_amount,
                'analytic_project_id': rec.account_project_id.id,
                'tci_id': tci_id,
            }

            new_line_rec = self.env['tci.line'].create(new_line)
            rec.tci_line_id = new_line_rec.id

            # Create new task if there none exist for the employee and wbs (to facilitate forecast)
            if rec.employee_id:
                task_exist = self.env['project.task'].search([('employee_id', '=', rec.employee_id.id),
                                                              ('account_project_id', '=', rec.account_project_id.id)])
                if not task_exist:
                    # Create task for the new employee record
                    task_name = str(rec.name_of_employee_or_applicant) + " - " + str(rec.account_project_id.name)
                    task_vals = {
                        'name': task_name,
                        'employee_id': rec.employee_id.id,
                        'account_project_id': rec.account_project_id.id,
                        'project_id': rec.project_id.id,
                        'etc_amount_calc_type': 'emp',
                    }
                    new_task = self.env['project.task'].create(task_vals)

        return True

