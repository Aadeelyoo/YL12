# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import api, fields, models, exceptions
import datetime


class TciAnalytics(models.AbstractModel):
    _name = 'tci.analytics'

    #company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    #currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)

    analytics_project_wbs_ids = fields.Many2many(relation='analytics_purchase_project_wbs_rel',
                                                 comodel_name='account.analytic_wbs.project',
                                                 column1='po_id', column2='project_wbs_id',
                                                 readonly=True, compute='compute_analytics_project_wbs_ids')

    @api.multi
    #@api.depends('tci_ids')
    def compute_analytics_project_wbs_ids(self, domain=False):
        print('compute_analytics_project_wbs_ids')
        model = self._name
        model_availables = ('purchase.order', 'project.project', 'res.partner', 'project.task', 'tci',
                            'account.analytic_wbs.project', 'account.analytic_wbs.account')
        if model not in model_availables:
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

        if not domain:
            domain = []
        print('domain 1 = %s' % domain)

        #self.test_run_sql()

        for record in self:
            print('domain 2 = %s' % domain)

            domain_tci = domain
            domain_forecast = domain
            print('domain_forecast 1 = %s' % domain_forecast)

            domain_incur_rec = domain
            project_wbs_grouped = []

            # add project_wbs IDS in outstanding TCIs
            '''
            domain_tci_add = [('is_outstanding', '=', True)]
            domain_tci.extend(domain_tci_add)
            domain_tci.append((search_field, '=', record.id))
            print('domain_forecast 1 = %s' % domain_forecast)

            tci_pwbs = self.env['tci.analytic.project'].search_read(domain_tci, ['analytic_project_id'])
            tci_wbs_ids = set([line['analytic_project_id'][0] for line in tci_pwbs])
            for rec in tci_wbs_ids:
                if not rec in project_wbs_grouped:
                    project_wbs_grouped.append(rec)

            '''
            # add project_wbs IDS in project.task.forecast

            print('domain_forecast 2 = %s' % domain_forecast)

            domain_forecast.append((search_field, '=', record.id))

            print('domain_forecast 3 = %s' % domain_forecast)
            forecast_pwbs = self.env['project.task.forecast'].search_read(domain_forecast, ['analytic_project_id'])
            forecast_wbs_ids = set([line['analytic_project_id'][0] for line in forecast_pwbs])
            for rec in forecast_wbs_ids:
                if not rec in project_wbs_grouped:
                    project_wbs_grouped.append(rec)

            # add project_wbs IDS in incurred recordings
            # Todo: add search for monthly recorded data

            record.analytics_project_wbs_ids = project_wbs_grouped

    # Computed Change request Money Values Fields
    @api.multi
    def _compute_cr_out(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='cr_out')

            rec.cr_out_debit = vals['debit']
            rec.cr_out_credit = vals['credit']
            rec.cr_out_balance = vals['balance']

    cr_out_balance = fields.Monetary(compute='_compute_cr_out', string='CR Out', store=False)
    cr_out_debit = fields.Monetary(compute='_compute_cr_out', string='CR Out Debit')
    cr_out_credit = fields.Monetary(compute='_compute_cr_out', string='CR Out Credit')

    # Computed LEMs Money Values Fields
    @api.multi
    def _compute_wt_out(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='wt_out')

            rec.wt_out_debit = vals['debit']
            rec.wt_out_credit = vals['credit']
            rec.wt_out_balance = vals['balance']

    wt_out_balance = fields.Monetary(compute='_compute_wt_out', string='LEM Out', store=False)
    wt_out_debit = fields.Monetary(compute='_compute_wt_out', string='LEM Out Debit')
    wt_out_credit = fields.Monetary(compute='_compute_wt_out', string='LEM Out Credit')

    # Computed Manual Accrual Values Fields
    @api.multi
    def _compute_maccr(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='maccr')

            rec.maccr_debit = vals['debit']
            rec.maccr_credit = vals['credit']
            rec.maccr_balance = vals['balance']

    maccr_balance = fields.Monetary(compute='_compute_maccr', string='Manual Accrual', store=False)
    maccr_debit = fields.Monetary(compute='_compute_maccr', string='Manual Accrual Debit')
    maccr_credit = fields.Monetary(compute='_compute_maccr', string='Manual Accrual Credit')

    # Computed Actuals Values Fields
    @api.multi
    def _compute_actual(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='actual')

            rec.actual_debit = vals['debit']
            rec.actual_credit = vals['credit']
            rec.actual_balance = vals['balance']

    actual_balance = fields.Monetary(compute='_compute_actual', string='Actuals', store=False)
    actual_debit = fields.Monetary(compute='_compute_actual', string='Actuals Debit')
    actual_credit = fields.Monetary(compute='_compute_actual', string='Actuals Credit')

    # Computed Open Commitment Values Fields
    @api.multi
    def _compute_open_commit(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='open_commit')

            rec.open_commit_debit = vals['debit']
            rec.open_commit_credit = vals['credit']
            rec.open_commit_balance = vals['balance']

    open_commit_balance = fields.Monetary(compute='_compute_open_commit', string='Open Commitment', store=False)
    open_commit_debit = fields.Monetary(compute='_compute_open_commit', string='Open Commitment Debit')
    open_commit_credit = fields.Monetary(compute='_compute_open_commit', string='Open Commitment Credit')

    # Computed Total Commitment Values Fields
    @api.multi
    def _compute_commitment(self):
        for rec in self:
            rec.commit_balance = rec.open_commit_balance + rec.actual_balance
    commit_balance = fields.Monetary(compute='_compute_commitment', string='Total Commitment', store=False)

    # Computed Invoices Values Fields
    @api.multi
    def _compute_invoice(self):
        for rec in self:
            vals = self.env['tci.analytic.project'].compute_tci_out_amt(rec, function='inv_out')

            rec.inv_out_debit = vals['debit']
            rec.inv_out_credit = vals['credit']
            rec.inv_out_balance = vals['balance']

    inv_out_balance = fields.Monetary(compute='_compute_invoice', string='INV Out', store=False)
    inv_out_debit = fields.Monetary(compute='_compute_invoice', string='Invoices Debit')
    inv_out_credit = fields.Monetary(compute='_compute_invoice', string='Invoices Credit')

    # Computed Accruals Values Fields
    @api.multi
    def _compute_accrual(self):
        for rec in self:
            rec.accrual_balance = rec.wt_out_balance + rec.inv_out_balance + rec.maccr_balance

    accrual_balance = fields.Monetary(compute='_compute_accrual', string='Accruals', store=False)

    # Computed Incurs Values Fields
    @api.multi
    def _compute_incur(self):
        for rec in self:
            rec.incur_balance = rec.actual_balance + rec.accrual_balance

    incur_balance = fields.Monetary(compute='_compute_incur', string='Incurred', store=False)

    # Computed ETC Values Fields
    @api.multi
    def _compute_etc(self):
        for rec in self:

            vals = self.env['project.task.forecast'].compute_etc_amt(rec)
            rec.etc_debit = vals['debit']
            rec.etc_credit = vals['credit']
            rec.etc_balance = vals['balance']

    etc_balance = fields.Monetary(compute='_compute_etc', string='Etc', store=False)
    etc_debit = fields.Monetary(compute='_compute_etc', string='Etc Debit')
    etc_credit = fields.Monetary(compute='_compute_etc', string='Etc Credit')

    # Computed EAC
    @api.multi
    def _compute_eac(self):
        for rec in self:
            rec.eac = rec.incur_balance + rec.etc_balance

    eac = fields.Monetary(compute='_compute_eac', string='EAC', store=False)


