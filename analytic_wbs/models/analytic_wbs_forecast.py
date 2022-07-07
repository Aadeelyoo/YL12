# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv
from datetime import datetime


class account_analytic_wbs_forecast_line(models.Model):
    _name = 'account.analytic_wbs.forecast_line'
    _description = 'wbs Forecast Line'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Description', required=True)
    date = fields.Date('Date', required=True, index=True, default=datetime.today())
    amount = fields.Monetary('Amount', compute='compute_amount', store=True)
    qty_amount = fields.Float('Quantity', default=0.0)
    mhr_amount = fields.Float('Man Hours', default=0.0)
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')
    line_transaction_id = fields.Many2one('account.analytic_wbs.forecast_transaction', 'Forecast Transaction', required=True, ondelete='cascade')
    forecast_transaction_state = fields.Selection(related="line_transaction_id.state", string="Transaction State", readonly=True, store=True)
    unit_rate = fields.Monetary('Unit Rate', default=0.0)

    project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State", readonly=True, store=True)
    partner_id = fields.Many2one(related="line_transaction_id.partner_id", string='Partner', readonly=True)

    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    tag_ids = fields.Many2many('account.analytic_wbs.tag', 'account_analytic_wbs_forecast_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)
    company_id = fields.Many2one('res.company', string = 'Company', required = True, default = lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    @api.depends('qty_amount', 'unit_rate')
    def compute_amount(self):
        for record in self:
            record.amount = record.qty_amount * record.unit_rate

    @api.onchange('account_project_id')
    def onchange_account_project(self):
        res = {}
        if self.line_transaction_id:
            ids = self.line_transaction_id.project_id.analytic_wbs_project_ids.mapped('id')
            res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res


    @api.multi
    def unlink(self):
        for order in self:
            if order.line_transaction_id.state != 'draft' and order.line_transaction_id.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" forecast transactions can be modified '))
        return super(account_analytic_wbs_forecast_line, self).unlink()


class account_analytic_wbs_forecast_transaction(models.Model):
    _name = 'account.analytic_wbs.forecast_transaction'
    _description = 'Forecast Transaction'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    @api.model
    def _default_name(self):
        seq_id = self.env['ir.sequence'].get('forecast.transaction.number')
        return self.env.context.get('name', seq_id)

    name = fields.Char('Forecast Transaction No', required=True, default=_default_name, track_visibility='onchange')
    date = fields.Datetime('Created', required=True, index=True, default=fields.Datetime.now)
    description = fields.Char('Description', required=False)
    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='restrict', track_visibility='onchange')
    transaction_type_id = fields.Many2one('account.analytic_wbs.forecast_transaction_type', 'Transaction Type', required=False, ondelete='restrict')
    transaction_detail_ids = fields.One2many('account.analytic_wbs.forecast_line', 'line_transaction_id', string='Transaction Detail')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
    ], default='draft', track_visibility='onchange')

    partner_id = fields.Many2one('res.partner', string='Partner', track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Created By', default=_default_user, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    @api.multi
    def _forecast_transaction_draft(self):
        self.write({ 'state' : 'draft' })
        return True

    @api.multi
    def _forecast_transaction_submitted(self):
        self.write({ 'state' : 'submitted' })
        return True

    @api.multi
    def _forecast_transaction_pending(self):
        self.write({'state': 'pending'})
        return True

    @api.multi
    def _forecast_transaction_approved(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def _forecast_transaction_posted(self):
        self.write({'state': 'posted'})
        return True

    @api.multi
    def _forecast_transaction_rejected(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and order.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" forecast transactions can be deleted '))
        return super(account_analytic_wbs_forecast_transaction, self).unlink()

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage' in init_values:
            return 'project.mt_progrtrans_stage'
        return super(account_analytic_wbs_forecast_transaction, self)._track_subtype(init_values)

    # Calculate Forecast Transaction Man Hours
    @api.multi
    def _compute_transaction_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.forecast_line']
        domain = [('line_transaction_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        transaction_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['line_transaction_id', 'mhr_amount'])
        line_transaction_ids = set([line['line_transaction_id'][0] for line in transaction_mhr_amounts])
        data_debit_mhr = {line_transaction_id: 0.0 for line_transaction_id in line_transaction_ids}
        data_credit_mhr = {line_transaction_id: 0.0 for line_transaction_id in line_transaction_ids}

        for transaction_mhr_amount in transaction_mhr_amounts:
            if transaction_mhr_amount['mhr_amount'] < 0.0:
                data_debit_mhr[transaction_mhr_amount['line_transaction_id'][0]] += transaction_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_mhr[transaction_mhr_amount['line_transaction_id'][0]] += transaction_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.transaction_mhr_debit = abs(data_debit_mhr.get(account.id, 0.0))
            account.transaction_mhr_credit = data_credit_mhr.get(account.id, 0.0)
            account.transaction_mhr_balance = account.transaction_mhr_credit - account.transaction_mhr_debit

    transaction_mhr_balance = fields.Float(compute='_compute_transaction_mhr', string='Mhr')
    transaction_mhr_debit = fields.Float(compute='_compute_transaction_mhr', string='Mhr Debit')
    transaction_mhr_credit = fields.Float(compute='_compute_transaction_mhr', string='Mhr Credit')

    # Calculate Forecast Transaction Amount
    @api.multi
    def _compute_transaction_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.forecast_line']
        domain = [('line_transaction_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        transaction_amounts = analytic_wbs_line_obj.search_read(domain, ['line_transaction_id', 'amount'])
        line_transaction_ids = set([line['line_transaction_id'][0] for line in transaction_amounts])
        data_debit_amt = {line_transaction_id: 0.0 for line_transaction_id in line_transaction_ids}
        data_credit_amt = {line_transaction_id: 0.0 for line_transaction_id in line_transaction_ids}

        for transaction_amount in transaction_amounts:
            if transaction_amount['amount'] < 0.0:
                data_debit_amt[transaction_amount['line_transaction_id'][0]] += transaction_amount[
                    'amount']
            else:
                data_credit_amt[transaction_amount['line_transaction_id'][0]] += transaction_amount[
                    'amount']

        for account in self:
            account.transaction_amt_debit = abs(data_debit_amt.get(account.id, 0.0))
            account.transaction_amt_credit = data_credit_amt.get(account.id, 0.0)
            account.transaction_amt_balance = account.transaction_amt_credit - account.transaction_amt_debit

    transaction_amt_balance = fields.Monetary(compute='_compute_transaction_amt', string='Amount')
    transaction_amt_debit = fields.Monetary(compute='_compute_transaction_amt', string='Amount Debit')
    transaction_amt_credit = fields.Monetary(compute='_compute_transaction_amt', string='Amount Credit')


class account_analytic_wbs_forecast_transaction_type(models.Model):
    _name = 'account.analytic_wbs.forecast_transaction_type'
    _description = 'Forecast Transaction Status'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    description = fields.Char('Description', required=True)
    order = fields.Integer('Order', default=99)
    is_active = fields.Boolean('Active', default=False)

    user_id = fields.Many2one('res.users', string='User', default=_default_user)