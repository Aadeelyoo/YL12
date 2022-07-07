# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class TaskForecast(models.Model):
    _name = 'project.task.forecast'
    _description = 'Task Forecasting'
    _order = 'date asc'

    name = fields.Char(required=False)

    def _get_default_wbs(self):
        res = self.task_id.account_project_id
        return self.env.context.get('analytic_project_id', res)

    task_id = fields.Many2one('project.task', string="Task", readonly=False, copy=True, ondelete='cascade')
    forecast_type = fields.Selection([
        ('forecast', 'Forecast'),
        ('plan', 'Planned Values'),
    ], string='Forecast Type', help="Forecast Type is used to differenciate the planned values from the ETC values.",
        default="forecast")

    date = fields.Date(string="Date", copy=True)
    date_y_m = fields.Char(string='Date Month', compute='get_date_y_m', store=True)
    quantity = fields.Float(string='Qty', store=True, readonly=False)
    unit_rate = fields.Float(string='Unit Rate', store=True, digits=dp.get_precision('Account'))
    amount = fields.Float(string='Amount', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    etc_contingency_percent = fields.Float(string='Contingency on ETC (%)', related='task_id.ect_contingency_percent')
    amount_etc_contingency = fields.Float(string='Contingency on ETC', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))

    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS',
                                          default=_get_default_wbs)
    project_id = fields.Many2one(related="analytic_project_id.project_id", string="Project", readonly=True, store=True)
    account_id = fields.Many2one(related="analytic_project_id.account_id", store=True)
    comment = fields.Char(string="Comment")

    po_id = fields.Many2one('purchase.order', related="task_id.po_id",
                            string='Purchase Order', readonly=True, store=True)
    po_internal_ref = fields.Char(related='po_id.internal_ref', store=True)
    partner_id = fields.Many2one('res.partner', related="task_id.po_id.partner_id",
                            string='Partner', readonly=True, store=True)
    sow_id = fields.Many2one('wbs.sow', related="task_id.sow_id",
                             string='SOW', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', related="task_id.employee_id",
                                  string='Employee', readonly=True, store=True)

    rep_uid = fields.Char(string='RepUID', compute='get_repuid', store=True)
    rep_name = fields.Char(string='Rep Name', compute='get_repuid', store=True)
    rep_uid_type = fields.Selection([
        ('emp', 'Employee'),
        ('po', 'Purchase Order'),
        ('task', 'Task'),
        ('other', 'Other'),
    ], string='Type', compute='get_repuid', help="Type is used to group the records in the reports.", store=True)

    @api.onchange('amount')
    def onchange_task_eac(self):
        for rec in self:
            rec.task_id.compute_eac()

    def get_default_wbs(self):
        if self.task_id.account_project_id:
            self.analytic_project_id = self.task_id.account_project_id.id

    @api.depends('analytic_project_id', 'po_id', 'employee_id', 'task_id', 'name')
    def get_repuid(self):
        for rec in self:
            wbs = str(rec.analytic_project_id.name) or False
            if rec.po_id:
                rep_name = str(rec.po_internal_ref) or str(rec.po_id.name) or False
                repuid = rep_name + "." + wbs
                rep_uid_type = 'po'
            elif rec.employee_id:
                rep_name = str(rec.employee_id.name)
                repuid = rep_name + "." + wbs
                rep_uid_type = 'emp'
            elif rec.task_id:
                rep_name = str(rec.task_id.name)
                repuid = rep_name + "." + wbs
                rep_uid_type = 'task'
            else:
                rep_name = 'other'
                repuid = rep_name + "." + wbs
                rep_uid_type = 'other'

            rec.rep_uid = repuid
            rec.rep_uid_type = rep_uid_type
            rec.rep_name = rep_name

    @api.onchange('po_id', 'employee_id', 'analytic_project_id')
    def onchange_rep_uid_def(self):
        for rec in self:
            rec.get_repuid()

    #@api.onchange('date')
    #def onchange_date(self):
    #    for rec in self:
    #        rec.get_date_y_m()

    @api.multi
    def incur_forecast_line(self):
        for rec in self:
            if not rec.po_id and not rec.employee_id:
                raise osv.except_osv(('Error'), ('Please assign PO or Employee to the task.'))
            elif not rec.analytic_project_id:
                raise osv.except_osv(('Error'), ('Please assign project wbs to the forecast line.'))
            else:
                #create manual accrual (tci)
                vals = {
                    'tci_type': 'maccr',
                    'reference': 'Manual incur from Forecast',
                    'description': rec.comment,
                    'po_id': rec.po_id.id,
                    'partner_id': rec.po_id.partner_id.id,
                    'employee_id': rec.employee_id.id,
                    'date': rec.date,
                }

                new_tci = self.env['tci'].create(vals)

                line_vals = {
                    'name': 'Manual Accrual',
                    'tci_id': new_tci.id,
                    'quantity': rec.quantity,
                    'unit_amount': rec.unit_rate,
                    'analytic_project_id': rec.analytic_project_id.id,
                }
                new_line = self.env['tci.line'].create(line_vals)
                rec.unlink()

                new_tci.update_analytic_project_line_ids()

    @api.depends('date')
    def get_date_y_m(self):
        for rec in self:
            if not rec.date:
                rec.date_y_m = ""
            elif rec.date.month <= 9:
                rec.date_y_m = str(rec.date.year) + "-0" + str(rec.date.month)
            elif rec.date.month >= 10:
                rec.date_y_m = str(rec.date.year) + "-" + str(rec.date.month)

    @api.multi
    @api.depends('quantity', 'unit_rate', 'etc_contingency_percent')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.unit_rate
            rec.amount_etc_contingency = rec.amount * rec.etc_contingency_percent / 100

    @api.onchange('task_id')
    def onchange_task_id(self):
        for rec in self:
            rec.analytic_project_id = rec.task_id.account_project_id

    # Compute Balance, Debit and Credit
    @api.multi
    def compute_etc_amt(self, rec, domain=False):
        rec.ensure_one()
        context = dict(self._context or {})
        model_availables = ('purchase.order', 'project.project', 'res.partner', 'project.task', 'tci',
                            'account.analytic_wbs.project', 'account.analytic_wbs.account')
        model = rec._name
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

            if not domain:
                domain = []

            domain.append((search_field, '=', rec.id))

            domain.append(('forecast_type', '=', 'forecast'))

            if self._context.get('from_date', False):
                domain.append(('date', '>=', self._context['from_date']))
            if self._context.get('to_date', False):
                domain.append(('date', '<=', self._context['to_date']))

            out_amts = self.env['project.task.forecast'].search_read(domain, [search_field, 'amount'])
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

    @api.model
    def create(self, vals):
        record = super(TaskForecast, self).create(vals)
        if not record.task_id:
            record.get_date_y_m()
            record.task_id._compute_etc()
        return record