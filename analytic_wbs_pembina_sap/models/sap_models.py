# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

EMPTY_DICT = {}


class DictDiffer(object):
    """Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current = set(current_dict)
        self.set_past = set(past_dict)
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])


class wbs_sap_import(models.Model):
    _name = 'sap.import'
    _description = 'SAP Import'
    _order = 'name'

    name = fields.Char(string='Name')
    sap_actuals_ids = fields.One2many('sap.actuals_line_mapped', 'sap_import_id', string='Actuals')
    sap_actuals_count = fields.Integer(string='Actuals Line Count', compute='get_actuals_count')

    sap_po_line_ids = fields.One2many('sap.po_line_mapped', 'sap_import_id', string='Po Lines')
    sap_po_line_count = fields.Integer(string='Po Line Count', compute='get_po_line_count')

    changed_sap_po_line_ids = fields.One2many('sap.po_line_mapped', 'last_change_sap_import_id', string='Changed Po Lines')
    changed_sap_po_line_count = fields.Integer(string='Changed Po Line Count', compute='get_changed_po_line_count')

    sap_open_po_ids = fields.One2many('sap.open_po_line_mapped', 'sap_import_id', string='Open POs')
    sap_open_po_count = fields.Integer(string='Open PO Line Count', compute='get_open_po_count')

    @api.multi
    def action_map_sap_import_content(self):

        '''Map data in po lines'''
        for record in self.sap_po_line_ids:
            # validate if the project_wbs exists
            if not record.account_project_id:
                wbs_project_id = self.get_wbs_id(record.wbs_element)
                if wbs_project_id:
                    record.account_project_id = wbs_project_id['project_wbs_id'].id
                    # todo: the 2 following lines should be deleted and set-up as related fields from account_project_id
                    record.account_id = wbs_project_id['account_id'].id
                    record.project_id = wbs_project_id['project_id'].id
                if not wbs_project_id:
                    # todo: IMPORTANT Create flag to the record here (warning Tag model)
                    print('FLAG FUNCTION TO CREATE. The record contain an empty wbs')

                    '''
                    raise UserError(_('Error on "SAP PO Lines Mapped" id %s.'
                                      'Project wbs -- %s -- not found and not created. Investigation required '
                                      'record = %s') % (record.id, record.wbs_element, record))
                    '''

            # record and link vendors
            if not record.vendor_id:
                vendor = record.get_vendor_info()
                if vendor:
                    record.vendor_id = vendor
                if not vendor:
                    # todo: IMPORTANT Create flag to the record here (warning Tag model)
                    print('vendor not fount and not created. Investigation required')
                    '''
                    raise Warning('vendor not fount and not created. Investigation required')
                    '''
            # record and link purchase orders
            if not record.purchase_order_id:
                po = record.get_purchase_order_info()
                if po:
                    record.purchase_order_id = po
                if not po:
                    # todo: IMPORTANT Create flag to the record here (warning Tag model)
                    print('purchase order not fount and not created. Investigation required')

                    _logger.warning('purchase order not fount and not created. Investigation required')

            if not record.purchase_order_line_id:
                po_line = record.get_purchase_order_line_info()
                if po_line:
                    record.purchase_order_line_id = po_line
                if not po_line:
                    # todo: IMPORTANT Create flag to the record here (warning Tag model)
                    _logger.warning('purchase order line not fount and not created. Investigation required')

        '''Map data in changed po lines'''

        for record in self.changed_sap_po_line_ids:
            # Get changed fields
            changed_fields = record.changed_fields
            print('changed fields = %s' % changed_fields)

            po_line = record.purchase_order_line_id

            changed_values = {}

            # Verify Po line pricing based on the Po line type from SAP (service line or material)
            # Service lines in SAP have a date in the created_on field, material lines do not have the date
            if record.created_on:
                print('material_po')
                print(record.purchasing_doc)
                if 'net_order_value' in changed_fields:
                    changed_values['product_qty'] = record.net_order_value

                if 'value_to_deliver' in changed_fields:
                    quantity_received = record.net_order_value - record.value_to_deliver
                    changed_values['qty_received'] = quantity_received

            if not record.created_on:
                print('material_po')
                print(record.purchasing_doc)
                if 'order_quantity' in changed_fields:
                    changed_values['product_qty'] = record.order_quantity

                if 'net_price' in changed_fields:
                    changed_values['price_unit'] = record.net_price

                if 'qty_to_deliver' in changed_fields:
                    quantity_received = record.order_quantity - record.qty_to_deliver
                    changed_values['qty_received'] = quantity_received

            if 'vendor' in changed_fields:
                print('need to create a function to change po_line vendor')

            if 'short_text' in changed_fields:
                changed_values['name'] = record.short_text

            if 'wbs_element' in changed_fields:
                code = record.wbs_element
                wbs_project_id = self.get_wbs_id(code)
                if wbs_project_id:
                    if wbs_project_id['project_wbs_id']:
                        changed_values['account_project_id'] = wbs_project_id['project_wbs_id'].id
                    if not wbs_project_id['project_wbs_id']:
                        print(record)
                        print('WBS Missing %s' % record.wbs_element)
                        # todo: needd to create a function that create the company WBS if mising or log error

                    # todo: Validate if we need to link account_id to the po line
                    # account_id is the company wbs not the project_wbs
                    #if wbs_project_id['account_id']:
                    #    record.account_id = wbs_project_id['account_id'].id
                    if wbs_project_id['project_id'] != po_line['project_id']:
                        changed_values['project_id'] = wbs_project_id['project_id'].id

            if 'deletion_indicator' in changed_fields:
                # todo: SAP Deletion indicator, Create function to update PO thru SAP dump
                print('need to create a function to change po_line deletion_indicator')

            if 'distribution_pcent' in changed_fields:
                # todo: SAP distribution percent, Link this info, update it ans display it somewhere
                print('do something with distribution percent')

            #print('changed_values = %s' % changed_values)
            po_line.update(changed_values)

        ''' Map data from Actuals'''
        for record in self.sap_actuals_ids:
            code = record.wbs_element
            wbs_project_id = self.get_wbs_id(code)
            if wbs_project_id:
                if wbs_project_id['project_wbs_id']:
                    if not wbs_project_id['project_wbs_id'].account_id.is_active:
                        record.unlink()
                    else:
                        record.account_project_id = wbs_project_id['project_wbs_id'].id
                if not wbs_project_id['project_wbs_id']:
                    print(record)
                    print('WBS Missing %s' % record.wbs_element)
                    # todo: needd to create a function that create the company WBS if mising or log error
                if wbs_project_id['account_id']:
                    record.account_id = wbs_project_id['account_id'].id
                if wbs_project_id['project_id']:
                    record.project_id = wbs_project_id['project_id'].id
            if record.purchasing_document:
                record.update_po_id()
            if record.name_of_employee_or_applicant:
                record.update_employee_id()

        self.link_actuals_tci()

        ''' Map data from Open PO'''
        self.link_open_commit_tci()

        new_po_ids = self.env['purchase.order'].search([('is_new_import', '=', True)])
        #print('new po = %s' % new_po_ids)
        for po in new_po_ids:
            po.create_task()
            po.is_new_import = False

    @api.multi
    def link_actuals_tci(self):
        # create tci for each document numbers in the actuals
        # get document number

        for record in self.sap_actuals_ids:
            if not record.tci_line_id:
                # search for existing doc numbers created in TCI
                exist_tci = self.env['tci'].search([('reference', '=', record.document_number), ('tci_type', '=', 'act')])
                if exist_tci:
                    # validate if there is a line with the same uid
                    uids = set()
                    for line in exist_tci.tci_line_ids:
                        uids.add(line.name)
                        if line.name == record.computed_uid:
                            print('need to create a function to do a dict diff and update values')
                            print('In theory, this should never happen')
                            # validate change

                    if not record.computed_uid in uids:
                        #create new line
                        new_tci_line = record.create_new_tci_line(tci_id=exist_tci.id)

                    exist_tci.update_analytic_project_line_ids()

                if not exist_tci:
                    #create the TCI
                    # todo: modify definition based on what type of actual this is
                    if record.employee_id:
                        no_mapping = True
                        # calculate current employee rate from actual
                        if not record.total_quantity == 0:
                            actual_timesheet_cost = record.val_ca_area_crcy / record.total_quantity
                        else:
                            actual_timesheet_cost = 0

                        # validate / update employee timesheet cost
                        if not record.employee_id.timesheet_cost == actual_timesheet_cost:
                            new_cost_val = {
                                'timesheet_cost': actual_timesheet_cost,
                            }
                            record.employee_id.update(new_cost_val)
                    else:
                        no_mapping = False
                    vals = {
                        'tci_type': 'act',
                        'description': 'SAP Actual',
                        'date': record.posting_date,
                        'reference': record.document_number,
                        'po_id': record.purchase_order_id.id,
                        'partner_id': record.purchase_order_id.partner_id.id,
                        # the line below is no longer required, superceeded by employee_id
                        # 'employee': record.name_of_employee_or_applicant,
                        'employee_id': record.employee_id.id,
                        'actual_mapped_id': record.id,
                        'parent_invoice_act_rel_id_no_link': no_mapping,
                        'account_ass_method': 'line',
                    }
                    new_tci = self.env['tci'].create(vals)

                    # search existing tasks for this newly recorded element.

                    # Search for employees
                    # Search for employee


                    # Search for PO
                    # Search for expenses

                    # Create the TCI lines
                    new_tci_line = record.create_new_tci_line(tci_id=new_tci.id)
                    new_tci.update_analytic_project_line_ids()

    @api.multi
    def link_open_commit_tci(self):
        # create tci for each document numbers in the actuals
        # get document number

        for record in self.sap_open_po_ids:
            #print('record = %s' % record)

            if not record.tci_line_id:
                # search for existing doc numbers created in TCI
                exist_tci = self.env['tci'].search([('reference', '=', record.ref_document_number), ('tci_type', '=', 'ocommit')])
                if exist_tci:
                    # Todo:   Change to update existing values (based on uid)
                    exist_line = self.env['tci.line'].search([('tci_id', '=', exist_tci.id), ('name', '=', record.computed_uid)], limit=1)
                    if exist_line:
                        # Update existing TCI_line
                        detail = {
                            'date': record.debit_date,
                            'unit_amount': record.val_ca_area_crcy,
                            'analytic_project_id': record.account_project_id.id,
                        }
                        exist_line.update(detail)
                    else:
                        #create new line
                        new_tci_line = record.create_new_tci_line(tci_id=exist_tci.id)
                        record.tci_line_id = new_tci_line
                    exist_tci.update_analytic_project_line_ids()

                if not exist_tci:
                    #create the TCI
                    vals = {
                        'tci_type': 'ocommit',
                        'description': 'SAP Open PO',
                        'date': record.document_date,
                        'reference': record.ref_document_number,
                        'po_id': record.purchase_order_id.id,
                        'partner_id': record.purchase_order_id.partner_id.id,
                        #'actual_mapped_id': record.id,
                        'parent_invoice_act_rel_id_no_link': True,
                        'account_ass_method': 'line',
                    }
                    new_tci = self.env['tci'].create(vals)
                    #print(new_tci)

                    # Create the TCI lines
                    new_tci_line = record.create_new_tci_line(tci_id=new_tci.id)
                    record.tci_line_id = new_tci_line
                    new_tci.update_analytic_project_line_ids()

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

                        raise Warning('Reference "%s" '
                                        'Invalid company wbs code in one of the lines to import. '
                                        'Modify the code or add the new company code into the database.'
                                        'Verify all level of the wbs string exist in the database.'
                                        % code)

                    if wbs_account_id and project_id:
                        #create the new project_wbs
                        exist_project_wbs = self.env['account.analytic_wbs.project'].search([('project_id', '=', project_id.id),
                                                                                             ('account_id', '=', wbs_account_id.id)])
                        # print('create project wbs %s with %s' % (project_id.name, wbs_account_id.name))
                        if not exist_project_wbs:
                            val = {
                                'project_id': project_id,
                                'wbs_id': wbs_account_id,
                            }
                            wbspid = self.env['account.analytic_wbs.project'].create_project_wbs(val)
                        else:
                            wbspid = exist_project_wbs
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
    def get_actuals_count(self):
        for record in self:
            record.sap_actuals_count = len(record.sap_actuals_ids)

    @api.multi
    def get_changed_po_line_count(self):
        for record in self:
            record.changed_sap_po_line_count = len(record.changed_sap_po_line_ids)

    @api.multi
    def get_open_po_count(self):
        for record in self:
            record.sap_open_po_count = len(record.sap_open_po_ids)

    @api.multi
    def action_import_sap_dump(self):
        # This is the main function called to map po_lines and the actuals from the dump import
        # import actuals dump
        actual = self.import_sap_actuals_dump()
        po_line = self.import_sap_po_line_dump()
        open_po = self.import_sap_open_po_dump()
        self.unlink_mapped_open_po_dump()

    @api.multi
    def import_sap_po_line_dump(self):
        # Verify if there is duplicated computed_uid in the dump lines
        dump_line_ids = self.env['sap.po_line_dump'].search([])

        # Todo: to delete
        for dump in dump_line_ids:
            dump.mapped = False
        #return False

        seen = set()

        for record in dump_line_ids:
            x = record.computed_uid
            if x in seen:
                #print('duplicate found %s' % x)
                self.env['sap.po_line_dump'].browse(record['id']).duplicate = True
            else:
                seen.add(x)

        # list all uid from env sap.po_line_mapped
        mapped_uids = []
        mapped_line_ids = self.env['sap.po_line_mapped'].search([])
        for mapped_line in mapped_line_ids:
            mapped_uids.append(mapped_line.computed_uid)

        # tag all dump lines already mapped
        for dump_line in dump_line_ids:
            if dump_line.computed_uid in mapped_uids:
                dump_line.mapped = True

        #return False

        mapped_dump_uids = self.env['sap.po_line_dump'].search([('mapped', '=', True),
                                                                ('duplicate', '=', False)])

        #print('mapped mapped_dump_uids len = %s' % len(mapped_dump_uids))
        #print('mapped mapped_dump_uids = %s' % mapped_dump_uids)

        for dump_line in mapped_dump_uids:
            #print('dump line already mapped %s' % dump_line.computed_uid)
            dumped_values = {}
            dumped_values = {
                'short_text': dump_line.short_text,
                'wbs_element': dump_line.wbs_element,
                'deletion_indicator': dump_line.deletion_indicator,
                'order_quantity': dump_line.order_quantity,
                'net_price': dump_line.net_price,
                'net_order_value': dump_line.net_order_value,
                'distribution_pcent': dump_line.distribution_pcent,
                'qty_to_deliver': dump_line.qty_to_deliver,
                'value_to_deliver': dump_line.value_to_deliver,
                'qty_to_invoice': dump_line.qty_to_invoice,
                'value_to_invoice': dump_line.value_to_invoice,
            }
            mapped_line = self.env['sap.po_line_mapped'].search([('computed_uid', '=', dump_line.computed_uid)], limit=1)
            if mapped_line:
                mapped_values = {}
                #print('mapped_line = %s' % mapped_line.computed_uid)
                mapped_values = {
                    'short_text': mapped_line.short_text,
                    'wbs_element': mapped_line.wbs_element,
                    'deletion_indicator': mapped_line.deletion_indicator,
                    'order_quantity': mapped_line.order_quantity,
                    'net_price': mapped_line.net_price,
                    'net_order_value': mapped_line.net_order_value,
                    'distribution_pcent': mapped_line.distribution_pcent,
                    'qty_to_deliver': mapped_line.qty_to_deliver,
                    'value_to_deliver': mapped_line.value_to_deliver,
                    'qty_to_invoice': mapped_line.qty_to_invoice,
                    'value_to_invoice': mapped_line.value_to_invoice,
                }

                diff = DictDiffer(dumped_values, mapped_values)
                diff_fields = []

                for field in diff.changed():
                    mapped_line[field] = dumped_values[field]
                    diff_fields.append(field)
                mapped_line['last_change_sap_import_id'] = self.id
                mapped_line['changed_fields'] = diff_fields

            dump_line.mapped = True

        # get all new dump lines to map and map them
        new_dump_line_ids = self.env['sap.po_line_dump'].search([('mapped', '=', False), ('duplicate', '=', False)])
        map_lines = []
        import_id = self.id
        for dump_line in new_dump_line_ids:
            map_lines.append({
                'sap_import_id': import_id,
                'document_date': dump_line.document_date,
                'purchasing_doc': dump_line.purchasing_doc,
                'sap_item': dump_line.sap_item,
                'vendor': dump_line.vendor,
                'short_text': dump_line.short_text,
                'wbs_element': dump_line.wbs_element,
                'deletion_indicator': dump_line.deletion_indicator,
                'seq_no_of_account_assgt': dump_line.seq_no_of_account_assgt,
                'computed_uid': dump_line.computed_uid,
                'net_price': dump_line.net_price,
                'net_order_value': dump_line.net_order_value,
                'order_quantity': dump_line.order_quantity,
                'created_on': dump_line.created_on,
                'distribution_pcent': dump_line.distribution_pcent,
                'qty_to_deliver': dump_line.qty_to_deliver,
                'value_to_deliver': dump_line.value_to_deliver,
                'qty_to_invoice': dump_line.qty_to_invoice,
                'value_to_invoice': dump_line.value_to_invoice,
            })
        lines = map(lambda x: (0, 0, self._return_list(x)), map_lines)
        self.write({'sap_po_line_ids': lines})
        new_dump_line_ids.write({'mapped': True})

        # delete all lines mapped from the data_dump
        self.env['sap.po_line_dump'].search([('mapped', '=', True), ('duplicate', '=', False)]).unlink()

        return True

    @api.multi
    def import_sap_actuals_dump(self):
        # remove all 'A00' and '-GL ' from the data dump
        removal_domain = ['|', ('wbs_element', 'ilike', '.A00'), ('cost_element_descr', 'ilike', '-GL ')]
        dump_to_remove = self.env['sap.actuals_line_dump'].search(removal_domain)
        dump_to_remove.unlink()

        # tag all dump lines with duplicate computed_uid
        dump_line_ids = self.env['sap.actuals_line_dump'].search_read([], fields=['computed_uid'])
        seen = set()
        for record in dump_line_ids:
            x = record['computed_uid']
            if x in seen:
                self.env['sap.actuals_line_dump'].browse(record['id']).duplicate = True
            else:
                seen.add(x)

        # list all uid from env sap.actuals_line_mapped
        mapped_uids = []
        mapped_line_ids = self.env['sap.actuals_line_mapped'].search([])
        for mapped_line in mapped_line_ids:
            mapped_uids.append(mapped_line.computed_uid)

        # tag all dump lines already mapped
        mapped_dump_uids = self.env['sap.actuals_line_dump'].search([('computed_uid', 'in', mapped_uids), ('duplicate', '=', False)])
        for dump_line in mapped_dump_uids:
            dump_line.mapped = True

        # get all dump lines to map and map them
        dump_line_ids = self.env['sap.actuals_line_dump'].search([('mapped', '=', False), ('duplicate', '=', False)])
        map_lines = []
        import_id = self.id
        for dump_line in dump_line_ids:
            map_lines.append({
                'sap_import_id': import_id,
                'document_date': dump_line.document_date,
                'posting_date': dump_line.posting_date,
                'document_number': dump_line.document_number,
                'ref_document_number': dump_line.ref_document_number,
                'object': dump_line.object,
                'purchasing_document': dump_line.purchasing_document,
                'sap_item': dump_line.sap_item,
                'vendor_name': dump_line.vendor_name,
                'name_of_employee_or_applicant': dump_line.name_of_employee_or_applicant,
                'cost_element_descr': dump_line.cost_element_descr,
                'name_of_offseting_account': dump_line.name_of_offseting_account,
                'val_ca_area_crcy': dump_line.val_ca_area_crcy,
                'transaction_currency': dump_line.transaction_currency,
                'total_quantity': dump_line.total_quantity,
                'document_header_text': dump_line.document_header_text,
                'project_definition': dump_line.project_definition,
                'fi_posting_item': dump_line.fi_posting_item,
                'wbs_element': dump_line.wbs_element,
                'recovery_indicator': dump_line.recovery_indicator,
                'posting_now': dump_line.posting_now,
                'computed_uid': dump_line.computed_uid,
                })
        lines = map(lambda x: (0, 0, self._return_list(x)), map_lines)
        self.write({'sap_actuals_ids': lines})
        dump_line_ids.write({'mapped': True})

        #delete all lines mapped from the data_dump
        self.env['sap.actuals_line_dump'].search([('mapped', '=', True), ('duplicate', '=', False)]).unlink()

        return True

    @api.multi
    def import_sap_open_po_dump(self):

        #tag all dump lines with duplicate computed_uid
        dump_line_ids = self.env['sap.open_po_line_dump'].search([])
        seen = {}
        for record in dump_line_ids:
            key = record['computed_uid']
            vals = {
                'val_ca_area_crcy': record['val_ca_area_crcy'],
                'document_date': record['document_date'],
                'ref_document_number': record['ref_document_number'],
                'reference_item': record['reference_item'],
                'sap_name': record['sap_name'],
                'project_definition': record['project_definition'],
                'wbs_element': record['wbs_element'],
                'deletion_indicator': record['deletion_indicator'],
                'vendor_no': record['vendor_no'],
                'deadline_item': record['deadline_item'],
                'debit_date': record['debit_date'],
                #'sap_line_mapped': record['sap_line_mapped'],
                'computed_uid': key,
            }
            if key not in seen:
                seen[key] = vals
            else:
                seen[key]['val_ca_area_crcy'] += vals['val_ca_area_crcy']

        # Map all dump lines
        map_lines = self.sap_open_po_ids.browse([])
        for line in seen.values():
            map_lines += map_lines.new(line)
        self.sap_open_po_ids = map_lines

        # Map PO and PO lines
        for rec in self.sap_open_po_ids:
            rec.update_po_id()
            rec.update_account_project()

    def unlink_mapped_open_po_dump(self):
        # Validate total amount and compare
        dump_line_ids = self.env['sap.open_po_line_dump'].search([])
        if dump_line_ids and self.sap_open_po_ids:
            total_dump_line = round(sum(dump.val_ca_area_crcy for dump in dump_line_ids), 2)
            total_map_line = round(sum(map.val_ca_area_crcy for map in self.sap_open_po_ids), 2)

            if total_dump_line == total_map_line:
                dump_line_ids.unlink()

            elif total_dump_line != total_map_line:
                pos = []
                for line in dump_line_ids:
                    if line.ref_document_number not in pos:
                        pos.append(line.ref_document_number)
                for po in pos:
                    po_dump_line_ids = self.env['sap.open_po_line_dump'].search([('ref_document_number', '=', po)])
                    po_mapped_line_ids = self.env['sap.open_po_line_mapped'].search([('ref_document_number', '=', po),
                                                                                     ('sap_import_id', '=', self.id)])
                    total_dump_line = round(sum(dump.val_ca_area_crcy for dump in po_dump_line_ids), 2)
                    total_map_line = round(sum(map.val_ca_area_crcy for map in po_mapped_line_ids), 2)

                    if total_dump_line == total_map_line:
                        po_dump_line_ids.unlink()
                    '''
                    elif total_dump_line != total_map_line:
                        print(po)
                        print('po_dump_line_ids lines = %s' % po_dump_line_ids)
                        print('total dump lines = %s' % total_dump_line)
                        print('po_mapped_line_ids lines = %s' % po_mapped_line_ids)
                        print('total map lines = %s' % total_map_line)
                    '''
                # Deleted raise Warning('The total amount of the new lines created does not equal. ')

    def _dump_actuals_tag_duplicated_uids(self):
        '''
        Tag all dump lines from sap_actuals_dump with duplicate computed_uid
        :return: list of all ids in sap_actuals_dump where computed_uid is a duplicate
        '''
        dump_line_ids = self.env['sap.actuals_line_dump'].search_read([], fields=['computed_uid'])
        seen = set()
        duplicate = set()
        for record in dump_line_ids:
            x = record['computed_uid']
            y = record['id']
            if x in seen:
                duplicate.add(y)
                self.env['sap.actuals_line_dump'].browse(record['id']).duplicate = True
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
    def action_map_po(self):
        self.env['sap.actuals_line_dump'].tag_actuals()

        '''
        removal_domain = ['|', ('wbs_element', 'ilike', 'A00'), ('cost_element_descr', 'ilike', '-GL ')]
        dump_to_remove = self.env['sap.actuals_line_dump'].search(removal_domain)
        dump_to_remove.unlink()
        '''

    @api.multi
    def action_test_button(self):
        for rec in self.sap_po_line_ids:
            rec.get_vendor_sap_code()

    @api.multi
    def get_tci_employee_id(self):
        tci_ids = self.env['tci'].search([('employee', '!=', False), ('employee_id', '=', False)])
        for rec in tci_ids:
            employee_id = self.env['hr.employee'].search([('name', '=', rec.employee)], limit=1)
            if not employee_id:
                new_emp_val = {
                    'name': rec.employee,
                }
                employee_id = self.env['hr.employee'].create(new_emp_val)
            rec.employee_id = employee_id.id


class wbs_sap_vendors(models.Model):
    _name = 'sap.vendors'
    _description = 'SAP Vendors'
    _order = 'vendor_no desc'

    dump_uid = fields.Char('Dump UID')
    sap_vendor_no = fields.Char(string='Computed SAP Vendor No')
    sap_vendor_name = fields.Char(string='Computed SAP Vendor No')


class wbs_sap_po(models.Model):
    _name = 'sap.po'
    _description = 'SAP Purchase Orders'
    _order = 'sap_po_no desc'

    sap_po_no = fields.Char('SAP PO Reference')
    _sql_constraints = [
        ('sap_po_no_uniq', 'unique (sap_po_no)', "Tag sap_po_no already exists !"),
    ]


class wbs_sap_po_lines(models.Model):
    _name = 'sap.po.lines'
    _description = 'SAP Purchase Orders Lines'
    _order = 'sap_po_no desc'

    sap_po_item = fields.Integer('SAP Item')
    seq_no_of_account_assgt = fields.Integer('Seq. No. of Account Assgt')


