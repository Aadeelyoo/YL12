# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import math
import base64
from logging import getLogger
import requests
import time
import json
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from odoo.osv import expression
from odoo.tools import pike_pdf_merge

logger = getLogger(__name__)

class TciTag(models.Model):
    _name = 'tci.tag'
    _description = 'Tci Tags'
    name = fields.Char(string='Tag', index=True, required=True)
    color = fields.Integer('Color Index')


class TCI_Tax(models.Model):
    _name = "tci.tax"
    _description = "TCI Tax"
    _order = 'sequence'

    def _compute_base_amount(self):
        tax_grouped = {}
        for tci in self.mapped('tci_id'):
            tax_grouped[tci.id] = tci.get_taxes_values()
        for tax in self:
            tax.base = 0.0
            if tax.tax_id:
                key = tax.tax_id.get_grouping_key({
                    'tax_id': tax.tax_id.id,
                    'account_id': tax.account_id.id,
                    'account_analytic_id': tax.account_analytic_id.id,
                })
                if tax.tci_id and key in tax_grouped[tax.tci_id.id]:
                    tax.base = tax_grouped[tax.tci_id.id][key]['base']
                else:
                    _logger.warning(
                        'Tax Base Amount not computable probably due to a change in an underlying tax (%s).',
                        tax.tax_id.name)

    tci_id = fields.Many2one('tci', string='TCI', ondelete='cascade', index=True)
    task_id = fields.Many2one(string="Task", readonly=True, related='tci_id.task_id', store=True, copy=False)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    account_id = fields.Many2one('account.account', string='Tax Account', required=True,
                                 domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of bill tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True,
                                 readonly=True)
    currency_id = fields.Many2one('res.currency', related='tci_id.currency_id', store=True, readonly=True)
    base = fields.Monetary(string='Base', compute='_compute_base_amount')

    @api.multi
    def _move_line_get(self):
        account_move = []
        for tax in self:
            account_move.append({
                'type': 'tax',
                'name': tax.name,
                'price_unit': tax.amount,
                'quantity': 1,
                'price': tax.amount,
                'account_id': tax.account_id.id,
                'tax_line_id': tax.tax_id.id,
            })
        return account_move


# todo: Compute TCI WBS based on account assignation method field
class TciAnalyticWBS(models.Model):
    _name = "tci.analytic.project"
    _description = "TCI Analytic Project"
    _order = 'tci_id, sequence'

    name = fields.Char(string='Reporting UID', compute='get_name', store=True)

    tci_id = fields.Many2one('tci', string='PC Document', ondelete='cascade', index=True, required=True)
    task_id = fields.Many2one(string="Task", related='tci_id.task_id', store=True, copy=False)
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS',
                                          ondelete='restrict', required=False)
    base_allocation = fields.Float(string='% Base Allocation', default='100')
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of bill wbs.")
    currency_id = fields.Many2one('res.currency', related='tci_id.currency_id', store=True)
    base = fields.Monetary(string='Base Amount')

    amount = fields.Monetary(string='Total Amount', compute='compute_all', store=True)
    calc_tci_line_percent = fields.Float(string='% of Overall', compute='compute_all')

    # todo: delete employee, replaced by employee_id
    employee = fields.Char(string='Employee Name - To delete', related='tci_id.employee')

    employee_id = fields.Many2one('hr.employee', string='Employee', related='tci_id.employee_id', store=True)
    po_id = fields.Many2one('purchase.order', related='tci_id.po_id', store=True)
    po_internal_ref = fields.Char(related='tci_id.po_id.internal_ref', store=True)
    partner_id = fields.Many2one('res.partner', related='tci_id.partner_id', store=True)
    project_id = fields.Many2one('project.project', related='analytic_project_id.project_id', store=True)
    project_code_id = fields.Char(related='analytic_project_id.project_id.project_code_id', store=True)
    state = fields.Selection(related='tci_id.state', store=True)
    tci_type = fields.Selection(related='tci_id.tci_type', store=True)
    account_id = fields.Many2one('account.analytic_wbs.account', related='analytic_project_id.account_id', store=True)

    tci_reference = fields.Char(related='tci_id.reference', store=True)
    tci_create_date = fields.Datetime(related='tci_id.create_date', store=True)
    tci_date = fields.Date(related='tci_id.date', store=True)
    tci_description = fields.Char(related='tci_id.description', store=True)

    is_outstanding = fields.Boolean(string='Outstanding', related='tci_id.is_outstanding', store=True)

    rep_uid = fields.Char(string='RepUID', compute='get_repuid', store=True)
    rep_name = fields.Char(string='Rep Name', compute='get_repuid', store=True)
    rep_uid_type = fields.Selection([
        ('emp', 'Employee'),
        ('po', 'Purchase Order'),
        ('task', 'Task'),
        ('other', 'Other'),
    ], string='Type', compute='get_repuid', help="Type is used to group the records in the reports.", store=True)

    @api.depends('po_id', 'employee_id', 'task_id', 'po_internal_ref', 'analytic_project_id', 'name')
    def get_repuid(self):
        for rec in self:
            wbs = str(rec.analytic_project_id.name) or False
            if rec.po_id:
                rep_name = str(rec.po_internal_ref) or str(rec.po_id.name) or False
                repuid = rep_name + "." + wbs
                rep_uid_type = 'po'
            elif rec.employee_id:
                rep_name = rec.employee_id.name
                repuid = rep_name + "." + wbs
                rep_uid_type = 'emp'
            elif rec.task_id:
                rep_name = rec.task_id.name
                repuid = rep_name + "." + wbs
                rep_uid_type = 'task'
            else:
                rep_name = 'other'
                repuid = rep_name + "." + wbs
                rep_uid_type = 'other'

            rec.rep_uid = repuid
            rec.rep_uid_type = rep_uid_type
            rec.rep_name = rep_name

    @api.depends('po_id', 'employee_id', 'task_id', 'analytic_project_id', 'po_internal_ref')
    def get_name(self):
        for line in self:
            rep = line.po_internal_ref or line.employee_id.name or line.task_id.name or 'other'
            line.name = str(rep) + str('.') + str(line.analytic_project_id.name)

    @api.depends('base', 'base_allocation', 'po_id', 'tci_id',
                 'tci_id.analytic_project_line_ids_total', 'analytic_project_id')
    def compute_all(self):
        for line in self:
            line.amount = line.base * line.base_allocation / 100

        for line in self:
            if line.tci_id.analytic_project_line_ids_total:
                line.calc_tci_line_percent = (line.amount / line.tci_id.analytic_project_line_ids_total) * 100
            else:
                line.calc_tci_line_percent = 0

    # Compute Balance, Debit and Credit
    @api.multi
    def compute_tci_out_amt(self, rec, function, domain=False):
        rec.ensure_one()
        context = dict(self._context or {})
        functions_availables = ('cr_out', 'wt_out', 'actual', 'inv_out', 'open_commit', 'maccr')
        model_availables = ('purchase.order', 'project.project', 'res.partner', 'project.task', 'tci',
                            'account.analytic_wbs.project', 'account.analytic_wbs.account', 'hr.employee')
        model = rec._name
        if function not in functions_availables:
            print('Function %s not available' % function)
            return False
        if model not in model_availables:
            print('Model %s not available' % model)
            return False
        else:
            # Get grouping field
            if model == 'purchase.order':
                search_field = 'po_id'
            if model == 'project.project':
                search_field = 'project_id'
            if model == 'res.partner':
                search_field = 'partner_id'
            if model == 'project.task':
                search_field = 'task_id'
            if model == 'tci':
                search_field = 'tci_id'
            if model == 'account.analytic_wbs.project':
                search_field = 'analytic_project_id'
            if model == 'account.analytic_wbs.account':
                search_field = 'account_id'
            if model == 'hr.employee':
                search_field = 'employee_id'

            if not domain:
                domain = []

            # define domain for outstanding Invoices
            if function == 'inv_out':
                # Todo:  Change all items in function here for outstanding boolean field
                domain_add = [('state', 'not in', ('rejected', 'void', 'released', 'completed', 'mapped')),
                              #('child_invoice_act_rel_ids', '=', False),
                              ('tci_type', '=', 'inv')]
            # define domain for outstanding Change Requests
            if function == 'cr_out':
                domain_add = [('state', 'not in', ('invoiced', 'void', 'released')),
                              ('tci_type', '=', 'cr')]
            # define domain for outstanding LEMs
            if function == 'wt_out':
                domain_add = [('state', 'not in', ('invoiced', 'void')),
                              ('tci_type', '=', 'wt')]
            # define domain for Manual Accrual
            if function == 'maccr':
                domain_add = [('state', 'not in', ('rejected', 'void')),
                              ('tci_type', '=', 'maccr')]
            # define domain for Actuals
            if function == 'actual':
                domain_add = [('tci_type', '=', 'act')]
            # define domain for Open Commitment
            if function == 'open_commit':
                domain_add = [('tci_type', '=', 'ocommit')]
            domain.extend(domain_add)
            domain.append((search_field, '=', rec.id))

            if self._context.get('from_date', False):
                domain.append(('date', '>=', self._context['from_date']))
            if self._context.get('to_date', False):
                domain.append(('date', '<=', self._context['to_date']))

            out_amts = self.env['tci.analytic.project'].search_read(domain, [search_field, 'amount'])
            field_ids = set([line[search_field][0] for line in out_amts])
            data_debit_amt = {field_id: 0.0 for field_id in field_ids}
            data_credit_amt = {field_id: 0.0 for field_id in field_ids}

            for out_amt in out_amts:
                if out_amt['amount'] < 0.0:
                    data_debit_amt[out_amt[search_field][0]] += out_amt['amount']
                else:
                    data_credit_amt[out_amt[search_field][0]] += out_amt['amount']

            out_amt_debit = abs(data_debit_amt.get(rec.id, 0.0))
            out_amt_credit = data_credit_amt.get(rec.id, 0.0)
            out_amt_balance = out_amt_credit - out_amt_debit

            vals = {
                'debit': out_amt_debit,
                'credit': out_amt_credit,
                'balance': out_amt_balance
            }
            return vals

    '''
    @api.multi
    def get_outstanding_project_wbs(self, domain=False):
        grouped_project_wbs = []
        lines = self.search_read(domain, ['analytic_project_id'])
        for rec in lines:
    '''


class TciWbsSplitLine(models.Model):
    _name = "tci.wbs_split_line"
    _description = "TCI Split by WBS"
    _order = 'id'

    tci_id = fields.Many2one('tci', string='TCI', ondelete='cascade', index=True)
    name = fields.Char(string='WBS Description', required=False)
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS')
    percent_split = fields.Float(string='% Allocation', default=100)
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one('res.currency', related='tci_id.currency_id', store=True, readonly=True)


class Tci(models.Model):
    _name = "tci"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'mail.approval']
    _description = "Project Control Cost Document"
    _order = "date desc, id desc"
    _parent_store = True

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.uid)

    name = fields.Char(string='Name', size=13, readonly=True,
                       help="Automaticly generated intrenal number")

    tci_type_id = fields.Many2one('tci.type', 'TCI Type', required=False, ondelete='restrict')
    tci_type = fields.Selection([
        ('act', 'Actuals'),
        ('ocommit', 'Open Commitment'),
        ('inv', 'Invoice'),
        ('wt', 'Work Ticket'),
        ('cr', 'Change Request'),
        ('maccr', 'Manual Accrual'),
        ('estimate', 'Estimate'),
    ], string='Type', copy=True, index=True, help="Type of cost item.")

    description = fields.Char(string='Description', readonly=True, required=False,
                              states={'new': [('readonly', False)],
                                      'draft': [('readonly', False)],
                                      'superuser_overwrite': [('readonly', False)],
                                      'review': [('readonly', False)],
                                      })
    date = fields.Date(readonly=True,
                       states={'new': [('readonly', False)],
                               'draft': [('readonly', False)],
                               'review': [('readonly', False)],
                               'superuser_overwrite': [('readonly', False)],
                               'void': [('readonly', False)]},
                       string="Document Date", copy=False)
    user_id = fields.Many2one('res.users', string='Assigned To', default=_default_user, track_visibility='onchange',
                              copy=False)

    tci_line_ids = fields.One2many('tci.line', 'tci_id', string='TCI Lines', copy=False, readonly=True,
                                   states={'new': [('readonly', False)],
                                           'draft': [('readonly', False)],
                                           'void': [('readonly', False)],
                                           'review': [('readonly', False)],
                                           'superuser_overwrite': [('readonly', False)],
                                           },
                                   )
    employee = fields.Char(string='Employee Name')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=False, readonly=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', change_default=True, required=False, readonly=False,
                                 states={'review': [('readonly', True)],
                                         'validated': [('readonly', True)],
                                         'invoiced': [('readonly', True)]},
                                 track_visibility='always', domain=[('is_company', '=', 'True')])
    project_ids = fields.Many2many(relation='tci_project_rel', comodel_name='project.project',
                                   column1='tci_id', column2='project_id', compute='compute_project_ids')
    analytic_project_ids = fields.Many2many(relation='tci_analytic_project_rel',
                                            comodel_name='account.analytic_wbs.project',
                                            column1='tci_id', column2='analytic_project_id',
                                            string='Project WBS',
                                            compute='compute_project_ids', store=True, search='_search_project_wbs')
    reference = fields.Char(string='Vendor Reference #', default='New',
                            help="The partner reference of this document.", readonly=True, required=False,
                            states={
                                'new': [('readonly', False)],
                                'draft': [('readonly', False)],
                                'review': [('readonly', False)],
                                'superuser_overwrite': [('readonly', False)],
                            })
    tax_line_ids = fields.One2many('tci.tax', 'tci_id', string='Tax Lines', readonly=True,
                                   states={'new': [('readonly', False)],
                                           'draft': [('readonly', False)],
                                           'superuser_overwrite': [('readonly', False)],
                                           'void': [('readonly', False)]}, copy=True)
    untaxed_amount = fields.Float(string='Subtotal', store=True, compute='_compute_amount',
                                  digits=dp.get_precision('Account'))
    tax_amount = fields.Float(string='Tax', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    total_amount = fields.Float(string='Total', store=True, compute='_compute_amount',
                                digits=dp.get_precision('Account'))
    # fields for auto-creation from data import
    unvalidated_amount = fields.Float(string='Unvalidated Amount', store=True, digits=dp.get_precision('Account'),
                                      help='Amount not validated used for data import')
    # project wbs definition
    analytic_project_line_ids = fields.One2many('tci.analytic.project', 'tci_id', string='WBS Lines', readonly=False,
                                                states={'new': [('readonly', False)],
                                                        'draft': [('readonly', False)],
                                                        'superuser_overwrite': [('readonly', False)],
                                                        'mapped': [('readonly', False)],
                                                        'void': [('readonly', False)]},
                                                copy=True)
    analytic_project_line_ids_total = fields.Float(string='WBS Total', store=False, compute='_compute_wbs_amount',
                                                   digits=dp.get_precision('Account'))
    analytic_project_line_ids_difference = fields.Float(string='WBS Diff.',
                                                        store=False,
                                                        compute='_compute_wbs_amount',
                                                        digits=dp.get_precision('Account'))
    analytic_project_line_ids_difference_pcent = fields.Float(string='WBS Diff. %',
                                                              store=False,
                                                              compute='_compute_wbs_amount',
                                                              digits=dp.get_precision('Account'))

    account_ass_method = fields.Selection([
        ('line', 'By Line'),
        ('tci', 'Overall')
    ], string='Account Assignation', default='line', copy=True,
        help="Cost assignation behaviour. By line item or by tci")
    by_tci_calc_method = fields.Selection([
        ('percent', 'By Percent'),
        ('amount', 'By Amount')
    ], string='Overall Calc. Method', default='percent', copy=True,
        help="Calculation method when using Account Assignation based on overall cost")
    tci_split_line_ids = fields.One2many('tci.wbs_split_line', 'tci_id', string='Tci Split Lines', readonly=True,
                                         states={'new': [('readonly', False)],
                                                 'draft': [('readonly', False)],
                                                 'review': [('readonly', False)],
                                                 'superuser_overwrite': [('readonly', False)],
                                                 'void': [('readonly', False)]}, copy=True)

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 states={'new': [('readonly', False)], 'draft': [('readonly', False)],
                                         'void': [('readonly', False)]},
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  states={'new': [('readonly', False)], 'draft': [('readonly', False)],
                                          'void': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    detail_description = fields.Text(string='Details')
    attachment_number = fields.Integer(compute='_compute_attachment', string='Number of Attachments')
    # todo: validate status requirements

    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('released', 'Released on PO'),
        ('invoiced', 'Invoiced'),
        ('completed', 'Completed'),
        ('mapped', 'Mapped'),
        ('superuser_overwrite', 'SuperUser Overwrite'),
        ('void', 'void')
    ], string='Status', copy=False, index=True, compute='_compute_state',
        readonly=False, store=True, search='_search_state', track_visibility='onchange',
        help="Status of the tci.")

    is_holdback = fields.Boolean(string='Holdback Invoice', default=False, readonly=False)
    is_void = fields.Boolean(string='Void', default=False, readonly=False)
    is_duplicate = fields.Boolean(string='Duplicate', default=False, readonly=False,
                                  compute='check_for_duplicate', store=False, search='_search_duplicate')
    possible_duplicate = fields.Boolean(string='Possible Duplicate', default=False, readonly=False,
                                  compute='check_for_duplicate', store=False)
    is_superuser_state = fields.Boolean(string='Superuser State', default=False, readonly=False)
    is_outstanding = fields.Boolean(string='Outstanding', readonly=True, compute='compute_outstanding_tci', store=True,
                                    help='All outstanding items are taken into consideration in the EAC calculations.')

    ready_to_submit = fields.Boolean(string='Ready to Submit', default=False, readonly=True,
                                     states={'new': [('readonly', False)]})
    task_id = fields.Many2one('project.task', string="Task", readonly=False, copy=False, ondelete='restrict')
    tci_line_count = fields.Integer(compute='compute_tci_line_count', string='Line Count')
    attachment_ids = fields.One2many(comodel_name="ir.attachment", inverse_name="res_id", compute="_compute_attachment",
                                     string="Attachment Files")

    po_id = fields.Many2one('purchase.order', string='Purchase Order', required=False, track_visibility='onchange')
    invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=False, copy=False)

    tci_template_id = fields.Many2one('tci.template', string='Document Template', readonly=True,
                                      states={'draft': [('readonly', False)], 'new': [('readonly', False)],
                                              'void': [('readonly', False)]})
    barcode = fields.Char(string='Barcode')
    # project_id_group = fields.Char(related='project_ids.name', store=True, string='Project')
    project_id_group = fields.Char(compute='_compute_group_by', store=True, string='Project')
    check_approval_process = fields.Boolean(
        string='Check Approval Process',
    )

    po_rev = fields.Char(string="PO Rev")

    external_uid = fields.Char(string="External UID")
    external_state = fields.Char(string="External State")
    external_soft_link = fields.Char(string="External App")
    external_doc_link = fields.Char(string="External Doc")

    color = fields.Integer(string='Color Index')

    # Parent / Childs

    parent_id = fields.Many2one('tci',
        string='Parent PC Doc',
        ondelete='restrict',
        index=True)

    child_ids = fields.One2many(
        'tci', 'parent_id',
        string='Child PC Docs',
        copy=False)

    parent_path = fields.Char(index=True)
    
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise models.ValidationError(
                'Error! You cannot create recursive tci.')

    is_back_to_vendor = fields.Boolean(string='Sent to Vendor', default=False, readonly=False, copy=False)
    back_to_vendor_date = fields.Datetime(string='To Vendor Date', readonly=False, copy=False)

    compute_domain_trigger = fields.Boolean(string='Compute Domains')

    actual_tci_ids = fields.Many2many(
        comodel_name='tci', relation='tci_tci_actual_rel',
        column1='tci_id', column2='actual_id', string="Actuals",
        domain=[('tci_type', '=', 'act')], help="List of actuals tci related")

    parent_invoice_act_rel_id_no_link = fields.Boolean(
        string='No invoice link', default=False, copy=False,
        help='Check to remove this line item from the unassigned SAP Actuals. To use when the actual is not linked to any logged invoice')
    parent_invoice_act_rel_id = fields.Many2one(
        'tci',
        string='Parent Invoice',
        domain=[('tci_type', '=', 'inv')],
        ondelete='restrict',
        copy=False,
        index=True)

    child_invoice_act_rel_ids = fields.One2many(
        'tci', 'parent_invoice_act_rel_id',
        help="List of invoices tci related",
        copy=False,
        string='Child Actuals')
    child_invoice_act_rel_amount = fields.Float(string='Actuals Subtotal', store=True,
                                                compute='_compute_child_invoice_act_amount',
                                                digits=dp.get_precision('Account'))

    parent_invoice_wt_rel_id = fields.Many2one(
        'tci',
        string='Parent Invoice',
        domain=[('tci_type', '=', 'inv')],
        ondelete='restrict',
        copy=False,
        index=True)

    child_invoice_wt_rel_ids = fields.One2many(
        'tci', 'parent_invoice_wt_rel_id',
        help="List of invoices tci related",
        copy=False,
        string='Child Lems')

    parent_cr_wt_rel_id = fields.Many2one(
        'tci',
        string='Parent Change Request',
        domain=[('tci_type', '=', 'cr')],
        ondelete='restrict',
        copy=False,
        index=True)

    child_cr_wt_rel_ids = fields.One2many(
        'tci', 'parent_cr_wt_rel_id',
        help="List related Lems",
        copy=False,
        string='Child Lems')

    flag_rate_tci = fields.Boolean(copy=False)

    '''
    parent_cr_id = fields.Many2one(
        'tci',
        string='Parent CR',
        domain=[('tci_type', '=', 'cr')],
        ondelete='restrict',
        index=True)

    child_cr_ids = fields.One2many(
        'tci', 'parent_cr_id',
        help="List of change requests tci related",
        string='Child CRs')


    parent_wt_id = fields.Many2one(
        'tci',
        string='Parent LEM',
        domain=[('tci_type', '=', 'wt')],
        ondelete='restrict',
        index=True)

    child_wt_ids = fields.One2many(
        'tci', 'parent_wt_id',
        help="List of change requests tci related",
        string='Child WTs')
    '''
    '''
    unassigned_wt_invoice_ids = fields.Many2many(comodel_name='tci', relation='unassigned_wt_invoice_rel',
                                                 column1='tci_id', column2='invoice_id', string="Invoices",
                                                 compute='get_unassigned_wt_invoice',
                                                 help="List of invoices tci related")

    @api.multi
    def get_unassigned_wt_invoice(self):
        for rec in self:
            po_id = rec.po_id.id
            res = self.env['tci'].search([('po_id', '=', po_id), ('tci_type', '=', 'wt'), ('parent_invoice_id', '=', False)])
            rec.unassigned_wt_invoice_ids = res.ids
    '''

    tag_ids = fields.Many2many('tci.tag', 'tci_tag_rel', 'tci_id', 'tag_id', string='Tags', copy=False, search='_search_tag')

    @api.multi
    #@api.depends('tci_type', 'reference', 'po_id', 'state')
    def check_for_duplicate(self):
        for rec in self:
            dup_recs = self.env['tci'].search([('tci_type', '=', rec.tci_type), ('reference', '=', rec.reference),
                                               ('po_id', '=', rec.po_id.id), ('state', '!=', 'void')])
            dup_list = []
            if len(dup_recs) > 1:
                # popup wizzard
                # todo: create wizzard to ask user what needs to be done with the duplicate
                for dup in dup_recs:
                    dup.is_duplicate = True
                    dup_list.append(dup.id)
            if not len(dup_recs) > 1:
                rec.is_duplicate = False

        return dup_list

    def action_open_tci(self):
        view_tree_id = self.env.ref('analytic_wbs.view_tci_line_tree').id
        view_id = self.env.ref('analytic_wbs.view_tci_line_form').id
        context = self._context.copy()

        action = {
            'name': _('TCI Details'),
            'view_mode': 'tree,form',
            'view_ids' : [
                (5, 0, 0),
                (0, 0, {'view_mode' : 'tree', 'view_id' : view_tree_id}),
                (0, 0, {'view_mode' : 'form', 'view_id' : view_id})],
            'res_model': 'tci.line',
            'type': 'ir.actions.act_window',
            'context': context,
            'nodestroy' : True,
            'target' : 'current',
            'domain': [('id', 'in', self.tci_line_ids.ids)],
        }
        return action

    def action_validate_rates(self):
        self.flag_rate_tci = False

        for line in self.tci_line_ids:
            if line.po_line_id and line.po_line_id.product_id:
                recs = self.env['product.supplierinfo'].sudo().search(
                    [('product_id', '=', line.po_line_id.product_id.id),
                     ('name', '=', line.po_line_id.order_id.partner_id.id)]
                )
                if not recs:
                    line.flag_rate = True
                else:
                    line.flag_rate = False

        if any(line.flag_rate for line in self.tci_line_ids):
            self.flag_rate_tci = True
        else:
            self.flag_rate_tci = False

    def action_zero_out_qty(self):
        for rec in self.tci_line_ids:
            rec.quantity = 0

    def _search_duplicate(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        return [('name', operator, value)]

    @api.depends('state', 'is_void', 'is_holdback')
    def compute_outstanding_tci(self):
        for rec in self:
            res = True
            tci_type = rec.tci_type

            # define domain for outstanding Invoices
            if tci_type == 'inv':
                if rec.state in ('rejected', 'void', 'released', 'completed', 'mapped', 'superuser_overwrite')\
                        or rec.is_holdback:
                    res = False

            # define domain for outstanding Change Requests
            elif tci_type == 'cr':
                if rec.state in ('invoiced', 'void', 'released', 'superuser_overwrite'):
                    res = False

            # define domain for outstanding LEMs
            elif tci_type == 'wt':
                if rec.state in ('completed', 'invoiced', 'void', 'rejected', 'superuser_overwrite'):
                    res = False

            # define domain for Manual Accruals
            elif tci_type == 'maccr':
                if rec.state in ('rejected', 'void'):
                    res = False
                else:
                    res - True

            # define domain for Actuals
            elif tci_type == 'act':
                res = True

            if not rec.is_outstanding == res:
                rec.is_outstanding = res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|', ('name', operator, name), ('reference', operator, name),
                      ('partner_id', operator, name), ('barcode', operator, name)]
        tci_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return self.browse(tci_ids).name_get()

    @api.one
    @api.depends('project_ids')
    def _compute_group_by(self):
        self.project_id_group = self.project_ids.ids

    @api.one
    @api.depends('tci_line_ids.untaxed_amount', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date')
    def _compute_amount(self):
        self.untaxed_amount = round(sum(line.untaxed_amount for line in self.tci_line_ids), 2)
        self.tax_amount = sum(line.amount for line in self.tax_line_ids)
        self.total_amount = self.untaxed_amount + self.tax_amount

    @api.one
    @api.depends('tci_line_ids', 'tci_line_ids.untaxed_amount', 'analytic_project_line_ids.amount', 'currency_id')
    def _compute_wbs_amount(self):
        total = sum(line.amount for line in self.analytic_project_line_ids)
        self.analytic_project_line_ids_total = total
        self.analytic_project_line_ids_difference = total - self.untaxed_amount
        if self.untaxed_amount:
            self.analytic_project_line_ids_difference_pcent = (self.analytic_project_line_ids_difference / self.untaxed_amount) * 100

    @api.depends('child_invoice_act_rel_ids', 'child_invoice_act_rel_ids.untaxed_amount', 'currency_id')
    def _compute_child_invoice_act_amount(self):
        for rec in self:
            rec.child_invoice_act_rel_amount = sum(line.untaxed_amount for line in rec.child_invoice_act_rel_ids)


    '''
    @api.multi
    def unlink(self):
        for tci in self:
            if not tci.state:
                continue
            elif tci.state not in ('new', 'draft', 'void'):
                raise UserError(_(
                    'You cannot delete a task cost item which is not new, draft or void. You should refund it instead.'))
        return super(Tci, self).unlink()
    '''

    @api.onchange('tci_line_ids', 'tci_line_ids.tci_line_tax_ids')
    def _onchange_tci_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
        return

    @api.onchange('tci_line_ids', 'account_ass_method', 'tci_split_line_ids', 'tci_split_line_ids.amount',
                  'by_tci_calc_method', 'tci_line_ids.analytic_project_id', 'tci_split_line_ids.percent_split')
    def _onchange_tci_line_analytic_project_id(self):
        print('self tci = %s' % self)
        self.update_analytic_project_line_ids()
        return

    '''
    @api.onchange('analytic_project_line_ids', 'analytic_project_line_ids.analytic_project_id',
                  'by_tci_calc_method')
    def _onchange_tci_split_line(self):
        print('onchange tci split line')
        if self.account_ass_method == 'line':
            print('method is line')
        else:
            print('do something here')
            rec = self.tci_split_line_ids
            print(rec)
        return
    '''

    @api.multi
    def trigger_domain_compute(self):
        if self.compute_domain_trigger:
            res = False
        else:
            res = True
        self.write({
            'compute_domain_trigger': res,
        })

    @api.onchange('po_id', 'partner_id', 'compute_domain_trigger')
    def compute_all_domain(self):
        domain_po_id = []
        # Validate if po_id belongs to partner_id
        if self.partner_id and not self.po_id:
            po_ids = self.env['purchase.order'].search([('partner_id', '=', self.partner_id.id)])
            domain_po_id = [('id', 'in', po_ids.ids)]

        if self.tci_type == 'act':
            domain = []
            if self.partner_id and not self.po_id:
                domain = [('partner_id', '=', self.partner_id.id), ('tci_type', '=', 'inv'), ('state', '!=', 'void')]
            elif self.po_id:
                domain = [('po_id', '=', self.po_id.id), ('tci_type', '=', 'inv'), ('state', '!=', 'void')]
            return {'domain': {'parent_invoice_act_rel_id': domain}}

        if self.tci_type == 'wt':
            domain_inv = []
            domain_cr = []
            if self.partner_id and not self.po_id:
                domain_inv = [('partner_id', '=', self.partner_id.id), ('tci_type', '=', 'inv'), ('state', '!=', 'void')]
                domain_cr = [('partner_id', '=', self.partner_id.id), ('tci_type', '=', 'cr'), ('state', '!=', 'void')]
            elif self.po_id:
                domain_inv = [('po_id', '=', self.po_id.id), ('tci_type', '=', 'inv'), ('state', '!=', 'void')]
                domain_cr = [('po_id', '=', self.po_id.id), ('tci_type', '=', 'cr'), ('state', '!=', 'void')]

            return {'domain': {'parent_invoice_wt_rel_id': domain_inv,
                               'parent_cr_wt_rel_id': domain_cr,
                               'po_id': domain_po_id,
                               }}

        if self.tci_type == 'inv':
            domain_wt = []
            domain_act = []
            if self.partner_id and not self.po_id:
                domain_wt = [('partner_id', '=', self.partner_id.id), ('tci_type', '=', 'wt'), ('state', '!=', 'void')]
                domain_act = [('partner_id', '=', self.partner_id.id), ('tci_type', '=', 'act'), ('state', '!=', 'void')]
            elif self.po_id:
                domain_wt = [('po_id', '=', self.po_id.id), ('tci_type', '=', 'wt'), ('state', '!=', 'void')]
                domain_act = [('po_id', '=', self.po_id.id), ('tci_type', '=', 'act'), ('state', '!=', 'void')]

            return {'domain': {'child_invoice_wt_rel_ids': domain_wt,
                               'child_invoice_act_rel_ids': domain_act,
                               }}

    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create a tci.tax line
        The line parameter is an tci.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        vals = {
            'tci_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.analytic_account_id.id or False,
            'account_id': tax['account_id'] or line.account_id.id,
        }
        # If the taxes generate moves on the same financial account as the expense bill line,
        # propagate the analytic account from the expense bill line to the tax line.
        # This is necessary in situations were (part of) the taxes cannot be reclaimed,
        # to ensure the tax move is allocated to the proper analytic account.
        if not vals.get('account_analytic_id') and line.analytic_account_id and vals[
            'account_id'] == line.account_id.id:
            vals['account_analytic_id'] = line.analytic_account_id.id

        return vals

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.tci_line_ids:
            price_unit = line.unit_amount
            taxes = line.tci_line_tax_ids.compute_all(
                price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.multi
    def get_wbs_values(self):
        wbs_grouped = {}
        if self.account_ass_method == 'line':
            for line in self.tci_line_ids:
                for wbs in line.analytic_project_id:
                    val = {
                        'tci_id': self.id,
                        # 'name': wbs['name'],
                        'analytic_project_id': wbs['id'],
                        'base': line['untaxed_amount'],
                        'base_allocation': 100,
                        'manual': False,
                    }
                    key = wbs
                    if key not in wbs_grouped:
                        wbs_grouped[key] = val
                    else:
                        wbs_grouped[key]['base'] += val['base']

        if self.account_ass_method == 'tci':
            calc_method = self.by_tci_calc_method
            for line in self.tci_split_line_ids:
                wbs = line.analytic_project_id
                if calc_method == 'percent':
                    base = self.untaxed_amount
                    base_allocation = line.percent_split
                elif calc_method == 'amount':
                    base = line.amount
                    base_allocation = 100
                else:
                    raise UserError(
                        _('Calculation Method does not exist.'))

                vals = {
                    'tci_id': self.id,
                    'analytic_project_id': wbs['id'],
                    'base': base,
                    'base_allocation': base_allocation,
                    'manual': False,
                }
                key = wbs
                if key not in wbs_grouped:
                    wbs_grouped[key] = vals
                # todo: create a sql constraint for uid not the same wbs twice for the same tci_id
        return wbs_grouped

    @api.multi
    def update_analytic_project_line_ids(self):
        print('update_analytic_project_line_ids')
        print('self = %s' % self)
        for rec in self:
            wbs_grouped = rec.get_wbs_values()
            wbs_lines = rec.analytic_project_line_ids.browse([])
            for wbs in wbs_grouped.values():
                wbs_lines += wbs_lines.new(wbs)
            rec.analytic_project_line_ids = wbs_lines
        return

    @api.multi
    def compute_tci_line_count(self):
        for tci in self:
            tci.tci_line_count = len(tci.tci_line_ids)

    # todo: Validate if the tci state needs to be propagated when the related task.id chances status (function below if from original code expense)
    @api.multi
    @api.depends('mail_approval_state', 'po_id', 'partner_id',
                 'parent_invoice_act_rel_id', 'po_rev', 'parent_invoice_wt_rel_id',
                 'mail_approval_start_date', 'is_void', 'tci_type', 'child_invoice_act_rel_ids')
    def _compute_state(self):
        for tci in self:
            if tci.is_superuser_state:
                state = 'superuser_overwrite'

            else:
                if tci.tci_type in ('wt', 'cr', 'estimate'):
                    if tci.parent_invoice_wt_rel_id:
                        state = 'invoiced'

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
                try:
                    tci.state = state
                except Exception as e:
                    print("somethin went wrong: " + str(e))


    def _search_state(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        return [('name', operator, value)]

    #Todo: complete search method
    def _search_tag(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        return [('name', operator, value)]

    def get_available_po_ids(self):
        if 'po_id_domain' in self._context:
            po_domain_ids = self._context['po_id_domain']
            po_ids = self.env['purchase.order'].search([('id', 'in', po_domain_ids)])
        else:
            po_ids = self.env['purchase.order'].search([])
            print(po_ids)
        return po_ids



    # todo: Manage template IDS and onchange events
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = {}
        # Validate if po_id belongs to partner_id
        if self.partner_id:
            po_ids = self.env['purchase.order'].search([('partner_id', '=', self.partner_id.id)])
            if self.po_id not in po_ids:
                self.po_id = False
            res['domain'] = {'po_id': [('id', 'in', po_ids.ids)]}
        else:
            res['domain'] = {'po_id': []}
            print(res)
            print(self._context)
        return res

    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        # Re initialize all inter tci links
        self.child_invoice_wt_rel_ids = False
        self.child_invoice_act_rel_ids = False
        self.child_cr_wt_rel_ids = False

        if self.po_id:
            # get partner_id if partner_id is False
            if self.partner_id and self.po_id.partner_id:
                if not self.partner_id == self.po_id.partner_id:
                    self.partner_id = self.po_id.partner_id

            if not self.partner_id and self.po_id.partner_id:
                self.partner_id = self.po_id.partner_id

            # get TCI templates related to the PO
            tci_template_ids = self.env['tci.template'].search([('po_id', '=', self.po_id.id)])
            if self.tci_template_id not in tci_template_ids:
                self.tci_template_id = False
            if self.tci_line_ids:
                for line in self.tci_line_ids:
                    line.po_id = False

            res['domain'] = {
                'tci_template_id': [('id', 'in', tci_template_ids.ids)],
                'child_invoice_act_rel_ids': [('tci_type', '=', 'act'), ('po_id', '=', self.po_id)],
                'child_invoice_wt_rel_ids': [('tci_type', '=', 'wt'), ('po_id', '=', self.po_id)],
                'child_cr_wt_rel_ids': [('tci_type', '=', 'wt'), ('po_id', '=', self.po_id)],
            }

        return res

    @api.multi
    @api.depends('po_id')
    def compute_tci_child_domain(self):
        project_grouped = []
        for record in self.mapped('analytic_project_line_ids'):
            for project in record.analytic_project_id.project_id:
                if project.id not in project_grouped and project.id:
                    project_grouped.append(project.id)
        if project_grouped:
            self.project_ids = project_grouped

    @api.onchange('tci_template_id')
    def import_template_lines(self):
        if self.tci_template_id:
            template = self.tci_template_id
            tci_template_lines = self._get_tci_template_line()
            tci_lines = self.tci_line_ids
            for line in tci_template_lines:
                tci_lines += tci_lines.new(line)
            self.tci_line_ids = tci_lines

            self.account_ass_method = template.account_ass_method
            self.by_tci_calc_method = template.by_tci_calc_method

            if template.tci_split_line_ids:
                self.tci_split_line_ids = False
                tci_template_split_lines = self._get_tci_template_split_line()
                tci_split_lines = self.tci_split_line_ids
                for line in tci_template_split_lines:
                    tci_split_lines += tci_split_lines.new(line)
                self.tci_split_line_ids = tci_split_lines

    @api.multi
    def _get_tci_template_line(self):
        tci_template_line = []
        company = self.po_id.company_id
        for line in self.tci_template_id.tci_template_line_ids:
            new_lines = {
                'product_id': line.product_id,
                'name': line.name,
                'description': line.description,
                'quantity': line.quantity,
                'uom_id': line.uom_id,
                'unit_amount': line.unit_amount,
                'analytic_project_id': line.analytic_project_id,
                'tci_id': self._origin.id,
                'company_id': company,
                'tci_line_tax_ids': line.tci_line_tax_ids,
            }
            tci_template_line.append(new_lines)
        return tci_template_line

    @api.multi
    def _get_tci_template_split_line(self):
        tci_template_split_line = []
        for line in self.tci_template_id.tci_split_line_ids:
            new_lines = {
                'name': line.name,
                'analytic_project_id': line.analytic_project_id,
                'percent_split': line.percent_split,
                'amount': line.amount,
                'tci_id': self._origin.id,
            }
            tci_template_split_line.append(new_lines)
        return tci_template_split_line


    # Return Wizard for selction of template
    @api.multi
    def action_use_templ_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approvers_overwrite',
            'view_id': self.env.ref('analytic_wbs.approver_overwite_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_tci_id': self.id,
                'default_po_id': self.po_id.id,
            },
            'target': 'new',
        }

    # Search approvers and return warning msg on Button METHOD
    @api.multi
    def get_template_approvers(self):
        res_id = self.id
        res_model = 'tci'
        current_approvers = self.env['mail.approvers'].sudo().search([
            ('res_id', '=', res_id),
            ('res_model', '=', res_model),
        ])
        if current_approvers:
            message = "Do you want to overwrite the current approvers with the new ones from the template"
            data = {
            		'default_tci_id': res_id,
            		'default_msg': message,
            		'unlink': True,
            		'approvers': current_approvers.ids,
                    }

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'approvers_overwrite',
                'view_id': self.env.ref('analytic_wbs.approver_overwite_form').id,
                'view_mode': 'form',
                'view_type': 'form',
                'context': data,
                'target': 'new',
            }
        else:
            self.create_tmpl_approvers(res_id, res_model, False, False)

    # Create approvers from templates
    def create_tmpl_approvers(self, res_id, res_model, unlink, approvers):
        if unlink:
            for appr in approvers:
                self.env['mail.approvers'].browse(appr).unlink()

        for line in self.tci_template_id.templ_approvers_ids:
            self.env['mail.approvers'].sudo().create({
                'res_id': res_id,
                'res_model': res_model,
                'user_id': line.user_id.id,
                'approval_type': line.activity_type.id,
            })
    '''
    @api.one
    @api.depends('analytic_project_line_ids.analytic_project_id')
    def compute_project_ids(self):
        project_grouped = []
        for record in self.mapped('analytic_project_line_ids'):
            for project in record.analytic_project_id.project_id:
                if project.id not in project_grouped and project.id:
                    project_grouped.append(project.id)
        if project_grouped:
            self.project_ids = 
    '''

    @api.one
    @api.depends('analytic_project_line_ids.analytic_project_id')
    def compute_project_ids(self):
        project_grouped = []
        project_wbs_grouped = []
        for record in self.mapped('analytic_project_line_ids'):
            if record.analytic_project_id.id not in project_wbs_grouped:
                project_wbs_grouped.append(record.analytic_project_id.id)
            if record.analytic_project_id.project_id.id not in project_grouped:
                project_grouped.append(record.analytic_project_id.project_id.id)
        if project_grouped:
            self.project_ids = project_grouped
        if project_wbs_grouped:
            self.analytic_project_ids = project_wbs_grouped

    @api.model
    def _search_project_wbs(self, operator, operand):
        """
        Search function for analytic_project_ids
        Do not use with operator 'not in'.
        """
        # todo Make it work with not in
        assert operator != "not in", "Do not search analytic_project_ids with 'not in'"
        tci_analytic_wbs = self.env['tci.analytic.project'].sudo().search([
            ('tci_id', '=', self.id),
            ('analytic_project_id', operator, operand)])
        # using read() below is much faster than tci_analytic_wbs.mapped('res_id')
        return [('id', 'in', [res['tci_id'] for res in tci_analytic_wbs.read(['tci_id'])])]

    @api.model
    def _search_project(self, operator, operand):
        """
        Search function for project_ids
        Do not use with operator 'not in'.
        """
        # todo Make it work with not in
        assert operator != "not in", "Do not search project_ids with 'not in'"
        tci_analytic_wbs = self.env['tci.analytic.project'].sudo().search([
            ('tci_id', '=', self.id),
            ('project_id', operator, operand)])
        # using read() below is much faster than tci_analytic_wbs.mapped('res_id')
        return [('id', 'in', [res['tci_id'] for res in tci_analytic_wbs.read(['tci_id'])])]

    @api.multi
    def _compute_attachment(self):
        for tci in self:
            tci.attachment_ids = self.env['ir.attachment'].search(
                [('res_model', '=', 'tci'), ('res_id', '=', tci.id)]).ids
            tci.attachment_number = len(tci.attachment_ids)

    @api.multi
    def action_rename_attachments(self):
        attachment_data = self.env['ir.attachment'].search(
            [('res_model', '=', 'tci'), ('res_id', 'in', self.ids)], order="id asc")
        for tci in self:
            # todo: change tci.reference to file name to ensure easy link to the vendor reference number
            base_fname = tci.name
            i = 0
            for file in attachment_data:
                i = i + 1
                ext = file.get_splitfile()['extension']
                xname = '_f_' + str(i)
                new_name = base_fname + xname + ext
                file.rename_file(new_name)

    @api.multi
    def view_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'project.task',
            'target': 'current',
            'res_id': self.task_id.id
        }

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'tci'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'tci', 'default_res_id': self.id}
        return res

    # Re-define the default name depends function
    @api.multi
    @api.depends('name', 'reference')
    def name_get(self):
        result = []
        for rec in self:
            if not rec.reference:
                name = rec.name
            else:
                name = str(rec.reference) + ' [' + str(rec.name) + ']'

            if rec.partner_id:
                name += ' ' + str(rec.partner_id.name)
            result.append((rec.id, name))
        return result

    @api.multi
    def action_draft(self):
        self.ensure_one()
        if not self.tci_line_ids:
            raise UserError(
                _('You cannot submit a tci without product lines. Add product lines to match the vendor cost item'))
        if not self.partner_id:
            raise UserError(
                _('Please assign the tci to the proper vendor prior to set it to the next stage'))
        self.ready_to_submit = True
        return True

    @api.multi
    def action_validate(self):
        self.ensure_one()
        self.verified = True
        return True

    @api.multi
    def action_unlock(self):
        self.ensure_one()
        self.verified = False
        return True

    @api.multi
    def action_tci_submit(self):
        self.ensure_one()
        #print('action submit')

        if self.flag_rate_tci:
            raise UserError(
                _('Please clear validation TCI Cost from Approved List.'))
        if not self.attachment_ids:
            raise UserError(
                _('Please add the attachment file prior to submit the record for approval. Attachment must be in a .PDF format'))
        pdf_files = self.attachment_ids.search([('res_model', '=', self._name), ('res_id', '=', self.id), ('mimetype', '=', 'application/pdf')])
        #print(pdf_files)
        if not pdf_files:
            raise UserError(
                _('Only files in .PDF format are allowed for submittal. Please add a new attachment file prior to submit.'))
        else:
            if not self.approval_document_ids:
                if len(pdf_files) == 1:
                    self.approval_document_ids = pdf_files.ids
                    self.action_mail_approval_start()
                    self.check_approval_process = True
                elif len(pdf_files) > 1:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'approval_attach_assign',
                        'view_id': self.env.ref('analytic_wbs.approval_attach_assign_form').id,
                        'view_mode': 'form',
                        'view_type': 'form',
                        'domain': [('mimetype', '=', 'application/pdf')],
                        'context': {
                                    'default_tci_id': self.id,
                                    },
                        'target': 'new',
                    }
            else:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'approval_attach_assign',
                        'view_id': self.env.ref('analytic_wbs.approval_attach_assign_form').id,
                        'view_mode': 'form',
                        'view_type': 'form',
                        'domain': [('mimetype', '=', 'application/pdf')],
                        'context': {
                                    'default_tci_id': self.id,
                                    'default_approval_document_ids': [(6,0,self.approval_document_ids.ids)],
                                    },
                        'target': 'new',
                    }


    @api.multi
    def action_tci_approve(self, feedback=False):
        self.ensure_one()
        activity_ids = self.get_current_user_approval_activity_ids()
        for activity in activity_ids:
            activity.action_feedback(feedback=feedback)

        if self.state == 'approved':
            self.create_merged_pdf()

    @api.multi
    def action_tci_approve_with_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval_feedback',
            'view_id': self.env.ref('analytic_wbs.approval_feedback_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_tci_id': self.id,
                'default_action': 'approve',
            },
            'target': 'new',
        }

    @api.multi
    def action_tci_reject_with_feedback(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval_feedback',
            'view_id': self.env.ref('analytic_wbs.approval_feedback_form').id,
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_tci_id': self.id,
                'default_action': 'reject',
            },
            'target': 'new',
        }

    @api.multi
    def action_tci_reject(self, feedback=False):
        self.ensure_one()
        activity_ids = self.get_current_user_approval_activity_ids()
        for activity in activity_ids[0]:
            activity.action_record_reject(feedback=feedback, delete_all=True)

        if self.state == 'rejected':
            self.create_merged_pdf()

    @api.multi
    def action_tci_void(self):
        self.ensure_one()
        self.is_void = True
        # Find activities and approvers and unlink
        res_model_id = self.env['ir.model'].search([('model', '=', self._name)]).id
        activity = self.env['mail.activity'].search([('res_model_id', '=', res_model_id), ('res_id', '=', self.id)])
        if activity:
            activity.unlink()
        # x approvers = self.env['mail.approvers'].search([('res_model', '=', 'tci'),('res_id', '=', self.id)])
        # x approvers.unlink()
        return True

    @api.multi
    def action_tci_reset_to_draft(self):
        self.ensure_one()
        if not self.is_void:
            self.action_tci_void()

        for approver in self.mail_approver_ids:
            approver.state = 'new'
        self.write({
            'is_void': False,
            'mail_approval_start_date': False,
            'mail_approval_end_date': False,
            'mail_approval_state': 'new',
            'approval_report_id': False,
        })
        self.message_post(body="State reset to Draft")
        self._compute_state()

        return True

    #Todo: Delete below function
    @api.multi
    def action_link_wt_invoice(self, context=False):
        self.ensure_one()
        print('self = %s' % self)
        print('context = %s' % context)
        print('_context = %s' % self._context)
        '''
        parent_tci_id = context['parent_tci_id']
        if not parent_tci_id:
            return False
        else:
            invoice = self.env['tci'].browse(parent_tci_id)
            print(invoice)
            print(self)

            print(self.parent_invoice_id)

            self.parent_invoice_id = parent_tci_id

            print(self.parent_invoice_id)
            #self['user_ids'].extend((4, user.id)
            #invoice.child_wt_ids =+ self.id
        '''

    @api.multi
    def get_sqeuence_number(self, tci_type=False):
        if tci_type == 'wt':
            seq = self.env['ir.sequence'].next_by_code('tci_wt_number') or '/'
        elif tci_type == 'cr':
            seq = self.env['ir.sequence'].next_by_code('tci_cr_number') or '/'
        elif tci_type == 'act':
            seq = self.env['ir.sequence'].next_by_code('tci_act_number') or '/'
        elif tci_type == 'inv':
            seq = self.env['ir.sequence'].next_by_code('tci_inv_number') or '/'
        elif tci_type == 'ocommit':
            seq = self.env['ir.sequence'].next_by_code('tci_ocommit_number') or '/'
        else:
            seq = self.env['ir.sequence'].next_by_code('tci.sequence') or '/'
        return seq

    # rec.update_duplicate_tag()
    #get duplicate items

    '''
    @api.onchange('reference', 'po_id', 'state', 'date')
    def update_duplicate_tag(self, old_dup_recs, new_dup_recs):
        dup_tag = self.env.ref('analytic_wbs.tci_tag_duplicate').id
        if old_dup_recs:
            print('old = %s' % old_dup_recs)
        if new_dup_recs:
            print('new = %s' % new_dup_recs)

        for old_rec in old_dup_recs:
            print(old_rec)
            print(old_rec.name)
            print(old_rec.tag_ids.ids)
            if dup_tag in old_rec.tag_ids.ids:
                print('a')
                #old_rec.tag_ids.write([(3, dup_tag)])
                print('r')

        for new_rec in new_dup_recs:
            if dup_tag not in new_rec.tag_ids.ids:
                print('b')
                new_rec.tag_ids.write([(4, dup_tag)])
    '''
    '''
        old = set(old_dup_recs)
        new = set(new_dup_recs)

        to_remove = old - new
        print('to remove %s ' % to_remove)

        to_create = new - old
        print('to create %s ' % to_create)

        self.env['tci_tag_rel'].search([('tci_id', 'in', old_dup_recs), ('tag_id', '=', dup_tag.id)])

        
        self.ensure_one()
        dup_recs = self.env['tci'].search([('tci_type', '=', self.tci_type), ('reference', '=', self.reference),
                                           ('po_id', '=', self.po_id.id), ('state', '!=', 'void'), ('date', '=', self.date)])
        print(dup_recs)

        if dup_recs:
            dup_tag = self.env.ref('analytic_wbs.tci_tag_duplicate')
            for rec in dup_recs:
                if dup_tag.id not in rec.tag_ids.ids:
                    rec.tag_ids.write([(4, dup_tag.id)])

        
        print(self.id)
        print(dup_list)
        dup_recs = self.env['tci'].search([('id', 'in', dup_list)])
        print(dup_recs)
        vals = {}
        for dup in dup_recs:
            val = {}
            if dup.date == self.date and dup_tag.id not in dup.tag_ids.ids:
                val = {
                    'tag_ids': [(4, dup_tag.id)],
                }
                dup.write(val)
            if dup.date != self.date and dup_tag.id in dup.tag_ids.ids:
                val = {
                    'tag_ids': [(3, dup_tag.id)],
                }
            #if val:
            #    dup.write(val)
    '''


    # Overriding Create Method
    @api.model
    def create(self, vals):
        res = super(Tci, self).create(vals)
        res.name = self.get_sqeuence_number(tci_type=res.tci_type)
        ean = generate_ean(res.name)
        res.barcode = ean
        res._onchange_tci_line_ids()
        res._onchange_tci_line_analytic_project_id()
        return res

    # Overriding Write Method
    @api.multi
    def write(self, vals):
        res = super(Tci, self).write(vals)
        return res

    # Overiding Copy Method
    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            reference=_("%s (copy)") % (self.reference or ''))
        if 'tci_line_ids' not in default:
            default['tci_line_ids'] = [(0, 0, line.copy_data()[0]) for line in self.tci_line_ids]
        # Read approvers
        approvers = self.mail_approver_ids
        res = super(Tci, self).copy(default)

        if approvers:
            for approver in approvers:
                vals = {
                    'res_model': self._name,
                    'res_id': res.id,
                    'user_id': approver.user_id.id,
                    'sequence': approver.sequence,
                    'approval_type': approver.approval_type.id
                }
                self.env['mail.approvers'].create(vals)
        return res

    # todo: To delete this function (this is a test function)
    def action_superuser_test_function(self):
        lems = self.env['tci'].search([('tci_type', '=', 'wt'), ('is_superuser_state', '=', True)])
        for lem in lems:
            #lem.action_superuser_state_true()
            lem.action_superuser_state_false()

    def action_superuser_state_true(self):
        self.write({
            'is_superuser_state': True
                   })
        self._compute_state()

    def action_superuser_state_false(self):
        self.write({
            'is_superuser_state': False
                   })
        self._compute_state()

    @api.multi
    def get_tci_type(self):
        self.ensure_one()
        res = dict(self._fields['tci_type'].selection).get(self.tci_type)
        return res

    def ir_action_create_status_report(self):
        for rec in self:
            if rec.state == 'approved':
                rec.create_merged_pdf()
            else:
                raise UserError(
                    _('Record %s is not approved. Status reports can only be created for "Approved" records' % rec.name))


    # Create merged attahments
    @api.multi
    def create_merged_pdf(self):

        for rec in self:
            if not rec.batch_id or rec.batch_id.state == 'draft':
                # generate pdf name
                pdf_name = str('Document Review Report - ') + str(rec.reference) + str(' - ') + str(rec.name) + str('.pdf')
                rec.approval_report_name = pdf_name

                # merger report
                decoded_data = []
                pdf_report = self.env.ref('analytic_wbs.report_for_solevo_tci_reportt').sudo().render_qweb_pdf([rec.id])[0]
                decoded_data.append(pdf_report)
                atts = rec.approval_document_ids.mapped('datas')

                merged_pdf = ""
                i = 0
                files = []
                atts.insert(0, base64.b64encode(pdf_report or b''))
                merged_pdf = pike_pdf_merge.process_from_stack(atts)

                # search for existing attachments for the field
                attach_ids = self.env['ir.attachment'].search([('res_model', '=', rec._name), ('res_id', '=', rec.id),
                                                               ('res_field', '=', 'approval_report_id')])
                if attach_ids:
                    attach_ids.unlink()


                ir_values = {
                    'name': pdf_name,
                    'type': 'binary',
                    'datas': base64.b64encode(merged_pdf),
                    'res_model': rec._name,
                    #'datas_fname': pdf_name,
                    'res_id': rec.id,
                    'res_field': 'approval_report_id',
                    'mimetype': 'application/pdf',
                }
                attachment = self.env['ir.attachment'].sudo().create(ir_values)

                rec.message_post(body="Document Review Report Created", attachment_ids=[attachment.id])

                '''
                rec.message_post(body="Validation Report Created", attachments=attachments)
                rec.approval_report_id = rec.attachment_ids.search([('name', '=', pdf_name),
                                                                      ('res_model','=','tci'),
                                                                      ('res_id','=',rec.id),
                                                                      ], limit=1).id
                '''
            else:
                print('no report created')


    # Send email with merged attahments
    @api.multi
    def send_by_email(self):
        '''
        This function opens a window to compose an email, with the daily_construction_report template message loaded by default
        '''
        self.ensure_one()

        # Remove Self Followers
        followers = self.env['mail.followers'].search([
            ('res_model', '=', 'tci'),
            ('res_id', '=', self.id)])
        for follower in followers:
            follower.sudo().unlink()

        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env.ref('analytic_wbs.email_template_tci_approved')
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        # Get approval report
        report = self.env['ir.attachment'].search([('res_field', '=', 'approval_report_id'), ('res_id', '=', self.id),
                                                   ('file_size', '!=', False), ('res_model', '=', 'tci')],
                                                  limit=1, order='id desc')
        if report:
            template_id.write({'attachment_ids': [(6, 0, [report.id])]})
        else:
            self.create_merged_pdf()
            template_id.write({'attachment_ids': [(6, 0, [report.id])]})
        '''
        attachment_ids = []
        for att in self.attachment_ids:
            attachment_ids.append(att.id)
        template_id.write({'attachment_ids': [(6, 0, attachment_ids)]})
        '''
        ctx = {
            'default_model': 'tci',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id.id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
        }
        # update send-out to vendor
        self.is_back_to_vendor = True
        self.back_to_vendor_date = datetime.now()
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


class TciControlAccount(models.Model):
    _name = "tci.control.account"
    _description = "TCI Control Account"

    name = fields.Char(string='Name', readonly=False, required=True)
    code = fields.Char(string='Code', required=True)


class TciLine(models.Model):
    _name = "tci.line"
    _description = "TCI Line"
    _order = "date desc, id desc"

    name = fields.Char(string='Internal Name', readonly=False)
    product_id = fields.Many2one('product.product', string='Product', readonly=True,
                                 states={'draft': [('readonly', False)],
                                         'void': [('readonly', False)],
                                         'new': [('readonly', False)]}, required=False)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, readonly=True,
                             states={'draft': [('readonly', False)],
                                     'void': [('readonly', False)],
                                     'review': [('readonly', False)],
                                     'new': [('readonly', False)]},
                             default=lambda self: self.env['uom.uom'].search([], limit=1, order='id'))
    unit_amount = fields.Float(string='Unit Price', readonly=True, required=True,
                               states={'draft': [('readonly', False)],
                                       'void': [('readonly', False)],
                                       'review': [('readonly', False)],
                                       'superuser_overwrite': [('readonly', False)],
                                       'new': [('readonly', False)]},
                               digits=dp.get_precision('Product Price'))
    quantity = fields.Float(required=True,
                            readonly=True,
                            states={'draft': [('readonly', False)],
                                    'void': [('readonly', False)],
                                    'review': [('readonly', False)],
                                    'superuser_overwrite': [('readonly', False)],
                                    'new': [('readonly', False)]},
                            digits=dp.get_precision('Product Unit of Measure'),
                            default=1)
    tci_line_tax_ids = fields.Many2many('account.tax', 'expense_tax', 'expense_id', 'tax_id', string='Taxes',
                                        readonly=True, default=False,
                                        states={'draft': [('readonly', False)], 'void': [('readonly', False)],
                                                'new': [('readonly', False)]})
    untaxed_amount = fields.Float(string='Amount', store=True,
                                  compute='_compute_amount', digits=dp.get_precision('Account'))
    total_amount = fields.Float(string='Total Amount', store=True,
                                compute='_compute_amount', digits=dp.get_precision('Account'))
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                          states={'post': [('readonly', True)], 'invoiced': [('readonly', True)]},
                                          oldname='analytic_account')
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS',
                                          states={'post': [('readonly', True)], 'invoiced': [('readonly', True)]})
    control_account_id = fields.Many2one('tci.control.account', string='Control Account', copy=True)
    account_id = fields.Many2one('account.account', string='Account',
                                 states={'post': [('readonly', True)], 'invoiced': [('readonly', True)]},
                                 default=lambda self: self.env['ir.property'].get('property_account_expense_categ_id',
                                                                                  'product.category'))
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of tci lines.")
    description = fields.Text()
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 states={'submit': [('readonly', False)]},
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related='tci_id.currency_id', string='Currency', readonly=True, store=True)
    state = fields.Selection(related="tci_id.state", string="Line State", readonly=False, store=True)
    tci_id = fields.Many2one('tci', string='TCI', ondelete='cascade', required=True, store=True)
    tci_type = fields.Selection(string="Type", readonly=True, related='tci_id.tci_type', store=True, copy=False)

    # Claiming quantities
    claim_qty = fields.Float(string='Claim Qty')
    claim_qty_uom = fields.Many2one('uom.uom', string='Claim UOM', required=False)

    # Todo: Add domain to po_line_id and tci_line_id
    po_line_id = fields.Many2one('purchase.order.line', string='PO Line', required=False,
                                 domain="[('order_id', '=', po_id)]")
    tci_cr_id = fields.Many2one('tci', string='TCI cr', ondelete='restrict', required=False,
                                domain="[('po_id', '=', po_id), ('tci_type', '=', 'cr')]")

    # Todo: Add default date value
    date = fields.Date(string="Date", copy=False)
    tci_date = fields.Date(string="Date", related='tci_id.date', store=True)

    partner_id = fields.Many2one('res.partner', string='Partner', related='tci_id.partner_id', store=True,
                                 readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='tci_id.employee_id', store=True,
                                 readonly=True)
    project_ids = fields.Many2many(relation='tci_line_project_rel', comodel_name='project.project',
                                   column1='tci_id', column2='project_id', readonly=True, )

    task_id = fields.Many2one(string="Task", readonly=True, related='tci_id.task_id', store=True, copy=False)
    po_id = fields.Many2one('purchase.order', related="tci_id.po_id", string='Purchase Order', readonly=True)
    flag_rate = fields.Boolean(copy=False)

    # new fields added here
    vendor_wbs = fields.Char("Vendor WBS")
    employee_name = fields.Char("Employee name")
    third_party_vendor = fields.Char("Third Party Vendor")
    third_party_doc_num = fields.Char("Third Party Doc#")
    line_percent_factor = fields.Float(default=100.0,string="Line Percent Factor")
    markup_percent =  fields.Float(default=0.0,string="Markup %")
    markup_value = fields.Float(string="Markup Value",compute='_compute_markup_value',store=False)

    @api.depends('markup_percent','line_percent_factor','untaxed_amount')
    def _compute_markup_value(self):
        for rec in self:
            rec.markup_value = (rec.untaxed_amount * rec.markup_percent) / 100


    # TODO: COMPLETE ON_CHANGE METHOD Below, project_was for the line should = the project wbs of the PO line selected

    @api.onchange('po_line_id')
    def onchange_po_line_id(self):
        if self.po_line_id and self.po_line_id.account_project_id:
            self.analytic_project_id = self.po_line_id.account_project_id.id


    @api.depends('quantity', 'unit_amount', 'tci_line_tax_ids', 'currency_id','markup_value','markup_percent','line_percent_factor')
    def _compute_amount(self):
        for tci in self:
            tci.untaxed_amount = (tci.unit_amount * tci.quantity) + (((tci.unit_amount * tci.quantity) * tci.markup_percent) / 100)
            tci.total_amount = (tci.unit_amount * tci.quantity)+ (((tci.unit_amount * tci.quantity) * tci.markup_percent) / 100)
            # tci.markup_value = (tci.untaxed_amount * tci.markup_percent) / 100

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name or ''
            self.unit_amount = self.product_id.price_compute('standard_price')[self.product_id.id]
            self.uom_id = self.product_id.uom_id
            # x no_tax_res_config = self.env['res.config.settings'].search([('model_tci_no_product_taxe', '=', True)])
            # x print(no_tax_res_config)
            # x if not no_tax_res_config:
            # remove default taxes
            # self.tci_line_tax_ids = self.product_id.supplier_taxes_id
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if self.product_id and self.uom_id.category_id != self.product_id.uom_id.category_id:
            raise UserError(
                _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure'))

    @api.multi
    def _compute_expense_totals(self, company_currency, account_move_lines, move_date):
        '''
        internal method used for computation of total amount of an expense in the company currency and
        in the expense currency, given the account_move_lines that will be created. It also do some small
        transformations at these account_move_lines (for multi-currency purposes)

        :param account_move_lines: list of dict
        :rtype: tuple of 3 elements (a, b ,c)
            a: total in company currency
            b: total in tci.line currency
            c: account_move_lines potentially modified
        '''
        self.ensure_one()
        total = 0.0
        total_currency = 0.0
        for line in account_move_lines:
            line['currency_id'] = False
            line['amount_currency'] = False
            if self.currency_id != company_currency:
                line['currency_id'] = self.currency_id.id
                line['amount_currency'] = line['price']
                line['price'] = self.currency_id.with_context(
                    date=move_date or fields.Date.context_today(self)).compute(line['price'], company_currency)
            total -= line['price']
            total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, account_move_lines

    @api.multi
    def _move_line_get(self):
        account_move = []
        for expense in self:
            if expense.account_id:
                account = expense.account_id
            elif expense.product_id:
                account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']
                if not account:
                    raise UserError(_(
                        "No Expense account found for the product %s (or for it's category), please configure one.") % (
                                        expense.product_id.name))
            else:
                account = self.env['ir.property'].with_context(force_company=expense.company_id.id).get(
                    'property_account_expense_categ_id', 'product.category')
                if not account:
                    raise UserError(_(
                        'Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))
            aml_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            move_line = {
                'type': 'src',
                'name': aml_name,
                'price_unit': expense.unit_amount,
                'quantity': expense.quantity,
                'price': expense.untaxed_amount,
                'account_id': account.id,
                'product_id': expense.product_id.id,
                'uom_id': expense.uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'tax_ids': expense.tci_line_tax_ids.ids,
            }
            account_move.append(move_line)
        return account_move

    @api.multi
    def unlink(self):
        for line in self:
            if line.state not in ('draft', 'new', 'void', 'superuser_overwrite'):
                raise UserError(_('Documents can only be deleted when in new, draft, void, or superuser states.'))
        return super(TciLine, self).unlink()


class TciLineAnalytic(models.Model):
    _name = "tci.line.analytic"
    _description = "TCI Line Analytic"
    _order = "name"

    tci_line_id = fields.Many2one('tci.line', string='TCI Line', ondelete='cascade', required=True)


class project_task_tci(models.Model):
    _inherit = "project.task"

    tci_line_ids = fields.One2many('tci.line', 'task_id', string='Expense Lines', readonly=True,
                                   states={'draft': [('readonly', False)], 'cancel': [('readonly', False)]}, copy=False)
    tci_ids = fields.One2many('tci', 'task_id', string='Expense Bills', readonly=True,
                              states={'draft': [('readonly', False)], 'cancel': [('readonly', False)],
                                      'review': [('readonly', False)]}, copy=False)
    sow_id = fields.Many2one('wbs.sow', string='SOW', required=False)
    tci_count = fields.Integer(compute='_compute_tci_count', string='TCI Count')

    @api.multi
    def _compute_tci_count(self):
        for record in self:
            record.tci_count = len(record.tci_ids)

    @api.multi
    def display_tci(self):
        self.ensure_one()
        res = {
            'name': 'TCI',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 80,
            'domain': [('task_id', '=', self.id)],
            'context': {
                'task_id': self.id,
                'default_task_id': self.id
            },
        }
        return res

    '''
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('review', 'Under Review'),
                              ('approve', 'Approved'),
                              ('post', 'Invoiced'),
                              ('invoiced', 'Paid'),
                              ('cancel', 'void')
                              ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='draft', required=True, help='Expense Report State')
   
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True,
        states={'submit': [('readonly', False)]}, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    address_id = fields.Many2one('res.partner', string="Employee Home Address")
    responsible_id = fields.Many2one('res.users', 'Validation By', readonly=True, copy=False,
        states={'submit': [('readonly', False)], 'submit': [('readonly', False)]})
    '''
    # todo: resolve cost computation for tasks
    '''
    total_untaxed_amount = fields.Float(string='Sub-Total Amount', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    total_tax_amount = fields.Float(string='Total Tax Amount', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    tax_line_ids = fields.One2many('tci.tax', 'task_id', string='Tax Lines', readonly=True,
        states={'draft': [('readonly', False)], 'cancel': [('readonly', False)], 'review': [('readonly', False)]}, copy=True)
    total_amount = fields.Float(string='Total Amount', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    '''

    # company_id = fields.Many2one('res.company', string='Company', readonly=True,
    #    states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id)

    # currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
    #    states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    # attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    # journal_id = fields.Many2one('account.journal', string='Expense Journal', states={'invoiced': [('readonly', True)], 'post': [('readonly', True)]},
    #    default=lambda self: self.env['ir.model.data'].xmlid_to_object('hr_solexpense.employee_expenses_journal') or self.env['account.journal'].search([('type', '=', 'purchase')], limit=1),
    #    help="The journal used when the expense is invoiced.")
    # bank_journal_id = fields.Many2one('account.journal', string='Bank Journal',
    #    states={'invoiced': [('readonly', True)], 'post': [('readonly', True)]}, default=lambda self: self.env['account.journal'].search([('type', 'in', ['case', 'bank'])], limit=1),
    #    help="The payment method used when the expense is paid by the company.")
    # accounting_date = fields.Date(string="Accounting Date")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', copy=False)

    # number = fields.Char(related='account_move_id.name', store=True, readonly=True, copy=False)
    # department_id = fields.Many2one('hr.department', string='Department',
    #    states={'post': [('readonly', True)], 'invoiced': [('readonly', True)]})

    # @api.multi
    # def check_consistency(self):
    #    if any(sheet.employee_id != self[0].employee_id for sheet in self):
    #        raise UserError(_("Expenses must belong to the same Employee."))

    '''
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('solexpense.sheet.sub.number') or '/'
            vals['name'] = seq
        # torq1 = vals.get('tci_ids')
        # torq2 = vals.get('tax_line_ids')
        sheet = super(project_task_tci, self).create(vals)
        # self.check_consistency()
        
        if vals.get('employee_id'):
            sheet._add_followers()
        
        return sheet
    '''

    # todo: most of the following actions can be deleted for the task
    '''
    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state == "post":
                raise UserError(_("You cannot delete a invoiced expense."))
        super(project_task_tci, self).unlink()

    @api.multi
    def set_to_paid(self):
        self.write({'state': 'invoiced'})

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approve':
            return 'hr_solexpense.mt_expense_approved'
        elif 'state' in init_values and self.state == 'submit':
            return 'hr_solexpense.mt_expense_confirmed'
        elif 'state' in init_values and self.state == 'cancel':
            return 'hr_solexpense.mt_expense_void'
        elif 'state' in init_values and self.state == 'invoiced':
            return 'hr_solexpense.mt_expense_paid'
        return super(project_task_tci, self)._track_subtype(init_values)

    def _add_followers(self):
        user_ids = []
        employee = self.employee_id
        if employee.user_id:
            user_ids.append(employee.user_id.id)
        if employee.parent_id:
            user_ids.append(employee.parent_id.user_id.id)
        if employee.department_id and employee.department_id.manager_id and employee.parent_id != employee.department_id.manager_id:
            user_ids.append(employee.department_id.manager_id.user_id.id)
        self.message_subscribe_users(user_ids=user_ids)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.address_home_id
        self.department_id = self.employee_id.department_id
    '''

    @api.one
    @api.depends('tci_ids', 'tci_ids.total_amount', 'tci_ids.untaxed_amount', 'tci_ids.tax_line_ids')
    def _compute_amount(self):
        self.total_untaxed_amount = sum(self.tci_ids.mapped('untaxed_amount'))
        self.total_amount = sum(self.tci_ids.mapped('total_amount'))
        self.total_tax_amount = sum(self.tax_line_ids.mapped('amount'))

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for tax in self.tax_line_ids:
            val = {
                'name': tax['name'],
                'tax_id': tax['tax_id'],
                'amount': tax['amount'],
                'sequence': tax['sequence'],
                'account_id': tax['account_id'],
                'account_analytic_id': tax['account_analytic_id'],
            }
            key = self.env['account.tax'].browse(tax['tax_id']).get_grouping_key(val)
            if key not in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['amount'] += val['amount']

        return tax_grouped

    # todo: Review validity of all actions listed below
    @api.model
    def _add_missing_default_values(self, values):
        values = super(project_task_tci, self)._add_missing_default_values(values)
        if self.env.context.get('default_tci_line_ids', False):
            lines_to_add = []
            for line in values.get('tci_line_ids', []):
                if line[0] == 1:
                    lines_to_add.append([4, line[1], False])
            values['tci_line_ids'] = lines_to_add + values['tci_line_ids']
        return values

    @api.one
    def _compute_attachment_number(self):
        self.attachment_number = sum(self.tci_ids.mapped('attachment_number'))

    '''
    @api.multi
    def submit_expense_sheets(self):
        self.write({'state': 'submit', 'responsible_id': self.env.user.id})

    @api.multi
    def refuse_expenses(self, reason):
        self.write({'state': 'cancel'})
        for sheet in self:
            body = (_(
                "Your Expense %s has been void.<br/><ul class=o_timeline_tracking_value_list><li>Reason<span> : </span><span class=o_timeline_tracking_value>%s</span></li></ul>") % (
                        sheet.name, reason))
            sheet.message_post(body=body)

    @api.multi
    def approve_expense_sheets(self):
        for bill in self.tci_ids:
            if not bill.verified:
                bill.verified = True
        self.write({'state': 'approve', 'responsible_id': self.env.user.id})

    '''

    @api.multi
    def action_sheet_move_create(self):
        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        res = self.mapped('tci_ids').action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        self.write({'state': 'post'})
        return res

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'tci'), ('res_id', 'in', self.tci_ids.ids)]
        res['context'] = {'create': False}
        return res

    @api.multi
    def action_open_journal_entries(self):
        res = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
        res['domain'] = [('id', 'in', self.mapped('account_move_id').ids)]
        res['context'] = {}
        return res

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        return self.state in ('draft', 'submit', 'review') and _('Draft Expense Report') or \
               self.state == 'approve' and _('Approved Expense Report') or \
               self.state in ('post', 'invoiced') and _('Expense Report - %s') % (self.number)


class tci_type(models.Model):
    _name = 'tci.type'
    _description = 'Task Cost Item Type'
    _order = 'name asc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.uid)

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    description = fields.Char('Description', required=True)
    order = fields.Integer('Order', default=99)
    is_active = fields.Boolean('Active', default=False)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)
