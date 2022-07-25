# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class WorkflowImport(models.Model):
    _name = 'workflow.import'
    _description = 'Workflow Import'
    _order = 'name'

    name = fields.Char(string='Name')

    workflow_mapped_ids = fields.One2many('workflow.invoice_mapped', 'workflow_import_id', string='Workflow Invoices')
    workflow_count = fields.Integer(string='Workflow Line Count', compute='get_workflow_count')

    changed_workflow_mapped_ids = fields.One2many('workflow.invoice_mapped', 'last_change_workflow_import_id',
                                                  string='Changed Mapped Lines')
    changed_workflow_mapped_count = fields.Integer(string='Changed Po Line Count',
                                                   compute='get_changed_workflow_mapped_count')

    @api.multi
    def action_map_workflow_invoice(self):

        ''' Map data in po lines '''
        for record in self.workflow_mapped_ids:
            # link purchase orders (records are not created if they don't already exist)
            record.update_po_id()

        ''' Create a new TCI for mapped workflow items '''
        rec_to_map = self.workflow_mapped_ids.search([('tci_id', '=', False), ('purchase_order_id', '!=', False)])

        for record in rec_to_map:
            untaxed_amount = record.invoice_amount
            vals = {
                'tci_type': 'inv',
                'description': 'External Invoice',
                'date': record.invoice_date,
                'reference': record.invoice_no,
                'po_id': record.purchase_order_id.id,
                'partner_id': record.purchase_order_id.partner_id.id,
                'workflow_mapped_id': record.id,
                'unvalidated_amount': record.invoice_amount,
                'external_uid': record.workflow_item,
                'external_state': record.status,
                'account_ass_method': 'tci',
            }

            new_tci = self.env['tci'].create(vals)
            record.tci_id = new_tci.id

            # update new_tci status
            if record.status == 'Void':
                new_tci.action_tci_void()

            if record.admin_url:
                adminvals = {
                    'res_model': 'tci',
                    'res_id': new_tci.id,
                    'name': 'Admin URL',
                    'description': 'Link to workflow Admin Page',
                    'type': 'url',
                    'url': record.admin_url,
                }
                admin_attach = self.env['ir.attachment'].create(adminvals)
                new_tci.external_soft_link = record.admin_url

            if record.invoice_url:
                invoicevals = {
                    'res_model': 'tci',
                    'res_id': new_tci.id,
                    'name': 'Invoice URL',
                    'description': 'Link to workflow invoice',
                    'type': 'url',
                    'url': record.invoice_url,
                }
                invoice_attach = self.env['ir.attachment'].create(invoicevals)
                new_tci.external_doc_link = record.invoice_url

            # verify if the PO uses default template for TCI
            default_template = self.env['tci.template'].search([('po_id', '=', record.purchase_order_id.id),
                                                                ('default_template', '=', True)], limit=1)
            if not default_template:
                po_wbs = new_tci.po_id.project_wbs_ids
                wbs_count = len(po_wbs)
                if wbs_count == 0:
                    wbs_count = 1
                default_value = new_tci.unvalidated_amount / wbs_count
                default_pcent = 100/wbs_count
                new_tci_lines = []
                new_tci_split_lines = []
                for wbs in po_wbs:
                    new_line = {
                        'name': 'Import from invoice',
                        'quantity': 1,
                        'unit_amount': default_value,
                        'analytic_project_id': wbs.id,
                        'tci_id': new_tci.id,
                    }
                    new_tci_lines.append(new_line)

                    new_split_line = {
                        'percent_split': default_pcent,
                        'amount': default_value,
                        'analytic_project_id': wbs.id,
                        'tci_id': new_tci.id,
                    }
                    new_tci_split_lines.append(new_split_line)

                for line in new_tci_lines:
                    new_tci.tci_line_ids.create(line)
                for split_line in new_tci_split_lines:
                    new_tci.tci_split_line_ids.create(split_line)

                new_tci.update_analytic_project_line_ids()

            if default_template:
                # Todo: Finalize default template use to create new tci invoice
                raise UserError(
                    _('Calculation Method does not exist for po with default tci template, Contact Yannick to create the function.'))

            # if tci lines value = 0, modify automatic tci state

    @api.multi
    def get_wbs_id(self, code):
        self.ensure_one()
        wbs_project_id = self.env['account.analytic_wbs.project'].get_project_wbs(code)
        result = {}
        if wbs_project_id:
            wbspid = wbs_project_id
            project_id = wbs_project_id.project_id
            wbs_account_id = wbs_project_id.account_id
        if not wbs_project_id:
            wbs_info = self.env['account.analytic_wbs.project'].extract_wbs_info(code)
            if not wbs_info:
                return False
            #get project id
            project_code = wbs_info['project']
            project_id = self.get_project_id(project_code)
            rec_len = len(wbs_info)
            for i in range(1, rec_len):
                wbspid = self.env['account.analytic_wbs.project'].get_project_wbs(wbs_info[i]['name'])
                if wbspid:
                    wbs_account_id = wbspid.account_id
                if not wbspid:
                    #get company_wbs id for the listed code
                    wbs_account_id = self.env['account.analytic_wbs.account'].get_wbs_account(wbs_info[i]['code'])
                    if not wbs_account_id:
                        # todo: IMPORTANT Create flag to the record here (warning Tag model)
                        print('Invalid company wbs code in one of the lines to import')
                        '''
                        raise Warning('Reference "%s" '
                                        'Invalid company wbs code in one of the lines to import. '
                                        'Modify the code or add the new company code into the database.'
                                        % code)
                        '''
                    if wbs_account_id and project_id:
                        #create the new project_wbs
                        val = {
                            'project_id': project_id,
                            'wbs_id': wbs_account_id,
                        }
                        wbspid = self.env['account.analytic_wbs.project'].create_project_wbs(val)
        result = {
            'project_id': project_id,
            'account_id': wbs_account_id,
            'project_wbs_id': wbspid,
        }
        return result


    @api.multi
    def get_project_id(self, code):
        #if project does not exist, raise error
        result = self.env['project.project'].search([('project_code_id', '=', code)])
        if result:
            return result
        else:
            # todo: Insert function to flag the line instead of stopping the program
            raise Warning('Reference "%s" Invalid project code in one of the lines to import. Validate the code or add the new project to the database.' % code)

    @api.multi
    def get_po_line_count(self):
        for record in self:
            record.sap_po_line_count = len(record.sap_po_line_ids)

    @api.multi
    def get_workflow_count(self):
        for record in self:
            record.workflow_count = len(record.workflow_mapped_ids)

    @api.multi
    def action_import_workflow_dump(self):
        # This is the main function called to map po_lines and the actuals from the dump import
        # import actuals dump
        invoices = self.import_workflow_line_dump()

    @api.multi
    def import_workflow_line_dump(self):
        dump_line_ids = self.env['workflow.invoice_dump'].search_read([], fields=['computed_uid'])
        seen = set()
        for record in dump_line_ids:
            x = record['computed_uid']
            if x in seen:
                print('duplicate found %s' % x)
                self.env['workflow.invoice_dump'].browse(record['id']).duplicate = True
            else:
                seen.add(x)

        # list all uid from env workflow.invoice_mapped
        mapped_uids = []
        mapped_line_ids = self.env['workflow.invoice_mapped'].search([])
        for mapped_line in mapped_line_ids:
            mapped_uids.append(mapped_line.computed_uid)

        # tag all dump lines already mapped
        mapped_dump_uids = self.env['workflow.invoice_dump'].search(
            [('computed_uid', 'in', mapped_uids), ('duplicate', '=', False)])
        for dump_line in mapped_dump_uids:
            # print('dump line already ,apped %s' % dump_line)
            dump_line.mapped = True

        # todo: Important, Create function to validate if workflow invoice status has change and if the status has change in the data dump, update the status of the mapped invoice


        #get all New dump lines to map and map them
        dump_line_ids = self.env['workflow.invoice_dump'].search([('mapped', '=', False), ('duplicate', '=', False)])
        map_lines = []
        import_id = self.id
        for dump_line in dump_line_ids:
            dump_vals = {
                'workflow_import_id': import_id,
                'sort_order': dump_line.sort_order,
                'workflow_item': dump_line.workflow_item,
                'current_step': dump_line.current_step,
                'status': dump_line.status,
                'current_user': dump_line.current_user,
                'vendor_no': dump_line.vendor_no,
                'vendor_name': dump_line.vendor_name,
                'invoice_no': dump_line.invoice_no,
                'invoice_amount': dump_line.invoice_amount,
                'invoice_date': dump_line.invoice_date,
                'scan_date': dump_line.scan_date,
                'po_no': dump_line.po_no,
                'invoice_url': dump_line.invoice_url,
                'admin_url': dump_line.admin_url,
                'comment_url': dump_line.comment_url,
                'history_url': dump_line.history_url,
                'bpm_url': dump_line.bpm_url,
                'computed_uid': dump_line.computed_uid,
                'payment_no': dump_line.payment_no,

            }
            map_lines.append(dump_vals)
            existing_mapped_line = self.env['workflow.invoice_mapped'].search([('computed_uid', '=', dump_line.computed_uid)], limit=1)
            if existing_mapped_line:
                map_vals = {
                    'workflow_import_id': import_id,
                    'sort_order': dump_line.sort_order,
                    'workflow_item': dump_line.workflow_item,
                    'current_step': dump_line.current_step,
                    'status': dump_line.status,
                    'current_user': dump_line.current_user,
                    'vendor_no': dump_line.vendor_no,
                    'vendor_name': dump_line.vendor_name,
                    'invoice_no': dump_line.invoice_no,
                    'invoice_amount': dump_line.invoice_amount,
                    'invoice_date': dump_line.invoice_date,
                    'scan_date': dump_line.scan_date,
                    'po_no': dump_line.po_no,
                    'invoice_url': dump_line.invoice_url,
                    'admin_url': dump_line.admin_url,
                    'comment_url': dump_line.comment_url,
                    'history_url': dump_line.history_url,
                    'bpm_url': dump_line.bpm_url,
                    'computed_uid': dump_line.computed_uid,
                    'payment_no': dump_line.payment_no,

                }

        lines = map(lambda x: (0, 0, self._return_list(x)), map_lines)
        self.write({'workflow_mapped_ids': lines})
        dump_line_ids.write({'mapped': True})

        # delete all lines mapped from the data_dump
        # todo: remove # below
        self.env['workflow.invoice_dump'].search([('mapped', '=', True), ('duplicate', '=', False)]).unlink()

        return True

    def _dump_workflow_tag_duplicated_uids(self):
        '''
        Tag all dump lines from workflow_invoice_dump with duplicate computed_uid
        :return: list of all ids in sap_actuals_dump where computed_uid is a duplicate
        '''
        dump_line_ids = self.env['workflow.invoice_dump'].search_read([], fields=['computed_uid'])
        seen = set()
        duplicate = set()
        for record in dump_line_ids:
            x = record['computed_uid']
            y = record['id']
            if x in seen:
                duplicate.add(y)
                self.env['workflow.invoice_dump'].browse(record['id']).duplicate = True
            else:
                seen.add(x)
        return list(duplicate)

    @api.multi
    def _sap_actuals_get_vendor_info(self):
        '''
        insert function
        :return:
        '''

    @api.multi
    def _return_list(self, line):
        return line

    @api.multi
    def get_changed_workflow_mapped_count(self):
        for record in self:
            record.changed_workflow_mapped_count = len(record.changed_workflow_mapped_ids)
