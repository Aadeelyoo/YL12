# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.osv import osv
from datetime import date, timedelta, datetime
import odoo.addons.decimal_precision as dp
import pandas as pd
from pandas.tseries.offsets import MonthEnd, MonthBegin
import numpy as np
import scipy.stats

import random

class TaskTci(models.Model):
    _inherit = ['project.task']

    tci_ids = fields.One2many(comodel_name='tci', inverse_name='task_id', string='Cost Items')
    tci_number = fields.Integer(compute='_compute_tci', string='Number of TCI')
    sow_id = fields.Many2one('wbs.sow', string='SOW', required=False, ondelete='restrict')

    etc_amount_calc_type = fields.Selection([
        ('manual', 'Manual'),
        ('rem_bdgt', 'Remaining Budget'),
        ('rem_bdgt_work', 'Remaining Working Budget'),
        ('emp', 'Employee Forecast'),
        ('po_cr', 'Po + CR OUT - Incurred'),
        ('manual_incur', 'Manual EAC - Incurred'),
        ('compute', 'Computed'),
    ], default='manual', string='ETC Calc. Type', copy=True,
        index=True, readonly=False, store=True,
        help="Select the calculation type you want to use to for the ETC amount.")
    etc_amount_compute = fields.Float(string='Computed ETC', store=True, compute='_compute_etc', digits=dp.get_precision('Account'))
    etc_amount_manual = fields.Float(string='Manual ETC', store=True, digits=dp.get_precision('Account'))
    etc_quantity_manual = fields.Float(string='Manual ETC Quantity', store=True)
    etc_amount = fields.Float(string='ETC',
                              store=False,
                              readonly=True,
                              compute='_compute_etc',
                              digits=dp.get_precision('Account'))
    ect_contingency_percent = fields.Float(string='Contingency on ETC (%)', default=10)
    incurred_amount_compute = fields.Float(string='Incurred', store=False, compute='_compute_etc', digits=dp.get_precision('Account'))

    eac_amount_manual = fields.Float(string='Manual EAC', store=True, digits=dp.get_precision('Account'))
    eac = fields.Float(string='EAC', compute='compute_eac', store=True, digits=dp.get_precision('Account'))

    po_value = fields.Float(string='PO Value', compute='_compute_etc', store=False, digits=dp.get_precision('Account'))
    cr_out = fields.Float(string='CR Out', compute='_compute_etc', store=False, digits=dp.get_precision('Account'))

    etc_distr_calc_type = fields.Selection([
        ('manual', 'Manual'),
        ('normal', 'Normal'),
        ('uniform', 'Uniform'),
        ('frontload', 'Front Load'),
        ('backload', 'Back Load'),
    ], default='manual', string='ETC Distr. Calc. Type', copy=True,
        index=True, readonly=False, store=True,
        help="Select the distribution type you want to use to for the ETC calculated by period.")
    etc_distr_calc_interval_size = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        #('bi-week', 'Bi-Weekly'),
        ('month', 'Monthly'),
    ], default='month', string='Distribution Interval', copy=True,
        index=True, readonly=False, store=True,
        help="Select the distribution type you want to use to for the ETC calculated by period.")
    etc_distr_date_start = fields.Date("ETC Distribution Start Date")
    etc_distr_date_end = fields.Date("ETC Distribution End Date")

    task_forecast_ids = fields.One2many('project.task.forecast', 'task_id', string='Forecast Items',
                                        domain=[('forecast_type', '=', 'forecast')])
    task_plan_ids = fields.One2many('project.task.forecast', 'task_id', string='Forecast Items',
                                    domain=[('forecast_type', '=', 'plan')])
    forecast_amount = fields.Float(compute='_compute_forecast_etc',
                                   string='Forecast ETC',
                                   digits=dp.get_precision('Account'),
                                   store=False)

    auto_forecast_calc = fields.Boolean('Auto Forecast Re-Calc', default=False,
                                        help="Auto forecast will re-calculate and re-generate the forecast curve everytime a calculation parameter is modified.")

    po_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=False)
    vendor_id = fields.Many2one('res.partner', string='Vendor', related='po_id.partner_id', store=True)

    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Default Project WBS', required=False)
    account_id = fields.Many2one('account.analytic_wbs.account', related='account_project_id.account_id', store=True)
    # todo: delete employee field, replaced by employee_id
    employee = fields.Char(string='Employee')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=False, readonly=False)

    rep_uid = fields.Char(string='RepUID', compute='get_repuid', store=True)
    rep_name = fields.Char(string='Rep Name', compute='get_repuid', store=True)
    rep_uid_type = fields.Selection([
        ('emp', 'Employee'),
        ('po', 'Purchase Order'),
        ('task', 'Task'),
        ('other', 'Other'),
    ], string='Type', compute='get_repuid', help="Type is used to group the records in the reports.", store=True)

    @api.depends('po_id', 'employee_id', 'account_project_id', 'name')
    def get_repuid(self):
        for rec in self:
            wbs = str(rec.account_project_id.name) or "wbs_not_defined"
            if rec.po_id:
                rep_name = str(rec.po_id.internal_ref) or str(rec.po_id.name) or False
                repuid = rep_name + "." + wbs
                rep_uid_type = 'po'
            elif rec.employee_id:
                rep_name = rec.employee_id.name
                repuid = rep_name + "." + wbs
                rep_uid_type = 'emp'
            else:
                rep_name = str(rec.name)
                repuid = rep_name + "." + wbs
                rep_uid_type = 'task'

            rec.rep_uid = repuid
            rec.rep_uid_type = rep_uid_type
            rec.rep_name = rep_name

    @api.onchange('po_id', 'employee_id', 'account_project_id', 'name')
    def onchange_rep_uid_def(self):
        for rec in self:
            rec.get_repuid()

    @api.multi
    def _compute_forecast_etc(self):
        for rec in self:
            value = sum(x.amount for x in rec.task_forecast_ids)
            rec.forecast_amount = value

    @api.depends('forecast_amount', 'incurred_amount_compute', 'task_forecast_ids', 'task_forecast_ids.amount',
                 'task_forecast_ids.quantity', 'task_forecast_ids.unit_rate')
    def compute_eac(self):
        for rec in self:
            if rec.etc_amount_calc_type in ('rem_bdgt','rem_bdgt_work'):
                rec.eac = rec.forecast_amount
            else:
                rec.eac = rec.forecast_amount + rec.incurred_amount_compute

    @api.multi
    #@api.depends('etc_amount_calc_type', '')
    def _compute_etc(self):
        for rec in self:
            if rec.etc_amount_calc_type == 'manual':
                rec.etc_amount = rec.etc_amount_manual

            if rec.etc_amount_calc_type == 'compute':
                rec.etc_amount_compute = 1
                rec.etc_amount = rec.etc_amount_compute

            # Calculate ETC based on remaining budget from WBS
            if rec.etc_amount_calc_type in ('rem_bdgt', 'rem_bdgt_work'):
                if not rec.account_project_id:
                    raise UserError(
                        _('The default project wbs field must not  be blank for this type of calculation.'))
                else:
                    p_wbs = rec.account_project_id
                    # get incurred cost
                    incurred = p_wbs.incur_balance
                    # get outstanding other etc
                    task_ids = self.env['project.task.forecast'].search([('analytic_project_id', '=', p_wbs.id),
                                                                         ('task_id', '!=', rec.id),
                                                                         ('forecast_type', '=', 'forecast')])
                    other_task_etc = sum(line.amount for line in task_ids)
                    # get p_wbs budget
                    if rec.etc_amount_calc_type == 'rem_bdgt':
                        budget = p_wbs.posted_bdgt_amt_balance
                    elif rec.etc_amount_calc_type == 'rem_bdgt_work':
                        budget = p_wbs.posted_bdgt_work_amt_balance

                    # calculate etc for the current task
                    etc = budget - incurred - other_task_etc

                rec.incurred_amount_compute = incurred
                rec.etc_amount_compute = etc
                rec.etc_amount = rec.etc_amount_compute
                rec.eac = etc
                rec.po_value = 0
                rec.cr_out = 0

            # Calculate ETC based on po value + outstanding CR or incurred cost
            if rec.etc_amount_calc_type in ('po_cr', 'manual_incur'):

                if not rec.account_project_id and rec.po_id:
                    raise UserError(
                        _('The default project wbs field must not be blank for this type of calculation and PO must be selected.'))

                else:
                    p_wbs = rec.account_project_id
                    rec_id = rec.po_id
                    # get incurred cost
                    inv_out_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='inv_out', domain=[('analytic_project_id', '=', p_wbs.id)])
                    inv_out = inv_out_val['balance']
                    actuals_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='actual', domain=[('analytic_project_id', '=', p_wbs.id)])
                    actuals = actuals_val['balance']
                    wt_out_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='wt_out', domain=[('analytic_project_id', '=', p_wbs.id)])
                    wt_out = wt_out_val['balance']
                    maccr_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='maccr', domain=[('analytic_project_id', '=', p_wbs.id)])
                    maccr_out = maccr_val['balance']

                    incurred = actuals + inv_out + wt_out + maccr_out

                    # Calculate PO value
                    if rec.etc_amount_calc_type == 'po_cr':
                        open_commit_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                            rec=rec_id, function='open_commit', domain=[('analytic_project_id', '=', p_wbs.id)])
                        open_commit = open_commit_val['balance']
                        po_value = open_commit + actuals
                        rec.po_value = po_value

                    if rec.etc_amount_calc_type == 'po_cr':
                        # get po value + out_cr value
                        cr_out_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                            rec=rec_id, function='cr_out', domain=[('analytic_project_id', '=', p_wbs.id)])
                        cr_out = cr_out_val['balance']
                        rec.cr_out = cr_out

                        #po_value = rec_id.amount_untaxed
                        calc_eac = cr_out + po_value

                    if rec.etc_amount_calc_type == 'manual_incur':
                        calc_eac = rec.eac_amount_manual
                        rec.po_value = 0
                        rec.cr_out = 0

                    eac = max((calc_eac, incurred))
                    # calculate etc for the current task
                    etc = eac - incurred

                rec.incurred_amount_compute = incurred
                rec.etc_amount_compute = etc
                rec.etc_amount = rec.etc_amount_compute
                rec.eac = eac

            # Calculate ETC based on po value + outstanding CR or incurred cost
            if rec.etc_amount_calc_type == 'emp':

                if not rec.account_project_id and rec.employee_id:
                    raise UserError(
                        _('The default project wbs field must not be blank for this type of calculation and Employee must be selected. %s' % rec.name))
                else:
                    p_wbs = rec.account_project_id
                    rec_id = rec.employee_id
                    # get incurred cost
                    inv_out_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='inv_out', domain=[('analytic_project_id', '=', p_wbs.id)])
                    inv_out = inv_out_val['balance']
                    actuals_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='actual', domain=[('analytic_project_id', '=', p_wbs.id)])
                    actuals = actuals_val['balance']
                    wt_out_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='wt_out', domain=[('analytic_project_id', '=', p_wbs.id)])
                    wt_out = wt_out_val['balance']
                    maccr_val = self.env['tci.analytic.project'].compute_tci_out_amt(
                        rec=rec_id, function='maccr', domain=[('analytic_project_id', '=', p_wbs.id)])
                    maccr_out = maccr_val['balance']

                    incurred = actuals + inv_out + wt_out + maccr_out

                    # Calculate etc from task
                    if rec.etc_amount_calc_type == 'emp':
                        domain = [('analytic_project_id', '=', p_wbs.id),
                                  ('task_id', '=', rec.id),
                                  ('employee_id', '=', rec_id.id),
                                  ('forecast_type', '=', 'forecast')]
                        forecast_line_ids = self.env['project.task.forecast'].search(domain)

                        etc = sum(line.amount for line in forecast_line_ids)

                rec.incurred_amount_compute = incurred
                rec.etc_amount_compute = etc
                rec.etc_amount = rec.etc_amount_compute
                rec.eac = incurred + etc
                rec.po_value = 0
                rec.cr_out = 0

    @api.multi
    def _compute_tci(self):
        for record in self:
            record.forecast_amount = sum(line.amount for line in record.task_forecast_ids)

    @api.onchange('etc_amount_calc_type','etc_amount_manual')
    def _onchange_etc_amount_calc_type(self):
        for rec in self:
            rec._compute_etc()

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

    @api.multi
    def display_forecast(self):
        self.ensure_one()
        res = {
            'name': 'Forecast',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.forecast',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 120,
            'domain': [('task_id', '=', self.id), ('forecast_type', '=', 'forecast')],
            'context': {
                'task_id': self.id,
                'default_task_id': self.id
            },
        }
        return res

    # todo: Deletete function below when tests are completed
    @api.multi
    def test_all_tasks_update(self):
        #print('test_all_tasks_update')
        test = self.get_distributed_values()
        #print(test)

    @api.multi
    def get_distributed_values(self):
        #print('get_distributed_values')
        date_format = "%Y-%m-%d"

        date_start = self.etc_distr_date_start
        date_end = self.etc_distr_date_end
        distribution_type = self.etc_distr_calc_type
        if date_end and date_start:
            if date_end < date_start:
                print('raise error date end mus be after date start')
            elif date_start and date_end:
                # print(date_start)
                etc = self.etc_amount

                dt = pd.to_datetime(date_start, format=date_format)
                dt1 = pd.to_datetime(date_end, format=date_format)

                # print(dt)
                # print(dt1)

                delta = (dt1 - dt)
                N = delta.days + 1
                # print(N)
                vals = []
                # normal distribution 0, 1
                if distribution_type == 'normal':
                    distr = scipy.stats.norm(0.5, 1 / 5)
                if distribution_type == 'uniform':
                    distr = scipy.stats.uniform()
                if distribution_type == 'frontload':
                    distr = scipy.stats.norm(0.3, 1 / 6)
                if distribution_type == 'backload':
                    distr = scipy.stats.norm(0.7, 1 / 6)

                period_probability = 0
                prob_cumul = 0

                for i in range(N):
                    period = self.get_period(dt + pd.DateOffset(i))
                    z = (i + 1) / N
                    if i == 0:
                        pdate = dt
                        probability = distr.cdf(z)
                    elif i == N - 1:
                        pdate = dt1
                        probability = 1 - prob_cumul
                    else:
                        pdate = dt + pd.DateOffset(i)
                        probability = distr.cdf(z) - distr.cdf(i / N)
                    prob_cumul += probability
                    # period for i + 1
                    period_next_i = self.get_period(dt + pd.DateOffset(i+1))
                    # print('i = %s , N = %s, date = %s , period_next_i = %s, period_i = %s' % (i, N, pdate, period_next_i, period))
                    period_probability += probability
                    if period != period_next_i or i == N - 1:
                        period_date = period.to_timestamp(how='E')
                        val = {
                            'period': period,
                            'date': period_date,
                            'period_probability': period_probability,
                            'prob_cumul': prob_cumul,
                            'period_value': period_probability * etc,
                            'p_cumul_value': prob_cumul * etc,
                        }
                        vals.append(val)
                        period_probability = 0
                        #print(val)

                return vals

    @api.multi
    def get_period(self, date=False):
        for rec in self:
            if date:
                frequence = rec.etc_distr_calc_interval_size

                if frequence == 'day':
                    ifreq = 'D'
                elif frequence == 'week':
                    ifreq = 'W'
                elif frequence == 'month':
                    ifreq = 'M'
                else:
                    ifreq = 'D'
                index = pd.Period(value=date, freq=ifreq or None)
                return index
            else:
                raise UserError(
                    _('missing date parameter'))
                return False

    @api.multi
    def test_forecast_gen(self):
        #print('test_forecast_gen')
        self.get_etc_distribution()

    @api.multi
    @api.depends('task_forecast_ids', 'task_forecast_ids.amount')
    def get_etc_distribution(self):
        #print('get_etc_distribution')

        for rec in self:
            #print('get_etc_distribution')
            # get distribution dates
            new_forecast = []
            wbs = rec.account_project_id
            unit_rate = 1
            if not rec.etc_distr_date_start or not rec.etc_distr_date_end or not rec.etc_distr_calc_interval_size or rec.etc_distr_date_start == rec.etc_distr_date_end:
                if rec.etc_distr_date_start:
                    vals = {
                        'task_id': self.id,
                        'date': rec.etc_distr_date_start,
                        'quantity': rec.etc_amount,
                        'unit_rate': 1,
                        'analytic_project_id': wbs.id,
                        'forecast_type': 'forecast',
                    }
                    new_forecast.append(vals)

                else:
                    return False

            else:
                index = self.get_distributed_values()
                if index[0] == False:
                    print('no dates')
                    return False
                #print(index)
                period_nb = len(index)
                # get ETC
                etc = rec.etc_amount
                if rec.etc_amount_calc_type == 'emp':
                    # get employee timesheet cost
                    if not rec.employee_id:
                        raise UserError(
                            _('Employee ID required for this type of forecast calculation'))
                    if rec.employee_id:
                        timesheet_cost = rec.employee_id.timesheet_cost
                        if not timesheet_cost:
                            raise UserError(
                                _('Please set-up the employee timesheet cost in the Employee Module'))

                if rec.etc_distr_calc_type not in ('normal', 'uniform', 'frontload', 'backload'):
                    raise UserError(
                        _('calculation for distribution calc type not defined'))

                if index[0]:
                    if rec.etc_distr_calc_type in ('normal', 'uniform', 'frontload', 'backload'):
                        if rec.etc_amount_calc_type == 'emp':
                            #xx period_qty = etc / (timesheet_cost * period_nb)
                            unit_rate = timesheet_cost
                            for fperiod in index:
                                date = fperiod['date']
                                period_qty = fperiod['period_value'] / timesheet_cost

                                vals = {
                                    'task_id': self.id,
                                    'date': date,
                                    'quantity': period_qty,
                                    'unit_rate': unit_rate,
                                    'analytic_project_id': wbs.id,
                                    'forecast_type': 'forecast',
                                }
                                new_forecast.append(vals)

                        else:
                            rounded_tot_unit = 0
                            cumul_total = 0
                            for fperiod in index:
                                date = fperiod['date']
                                period_qty = fperiod['period_value']
                                #unit_rate = fperiod['period_probability']
                                if not fperiod == index[-1]:
                                    unit_rate = round(period_qty / etc, 2) or 0
                                    rounded_tot_unit += unit_rate
                                    cumul_total += round((etc * unit_rate), 2)
                                else:
                                    unit_rate = 1 - rounded_tot_unit
                                    cumul_total += round((etc * unit_rate), 2)

                                vals = {
                                    'task_id': self.id,
                                    'date': date,
                                    'quantity': etc,
                                    'unit_rate': unit_rate,
                                    'analytic_project_id': wbs.id,
                                    'forecast_type': 'forecast',
                                }
                                new_forecast.append(vals)

                                if fperiod == index[-1]:
                                    diff = etc - cumul_total
                                    if diff != 0:
                                        vals = {
                                            'task_id': self.id,
                                            'date': date,
                                            'quantity': diff,
                                            'unit_rate': 1,
                                            'analytic_project_id': wbs.id,
                                            'forecast_type': 'forecast',
                                        }
                                        new_forecast.append(vals)

                            # append empty forecast line
                            period_qty = 0
                            unit_rate = 1

                            vals = {
                                'task_id': self.id,
                                'date': date,
                                'quantity': period_qty,
                                'unit_rate': unit_rate,
                                'analytic_project_id': wbs.id,
                                'forecast_type': 'forecast',
                            }
                            new_forecast.append(vals)

            # todo: change the current forecast search to filter on forecast type as well.
            current_forecast = self.env['project.task.forecast'].search([('task_id', '=', self.id),
                                                                         ('forecast_type', '=', 'forecast')])
            if rec.etc_distr_calc_type != 'manual':
                current_forecast.unlink()
            for forecast in new_forecast:
                rec.task_forecast_ids.create(forecast)

    @api.multi
    def get_etc_distr_function(self):
        print('test12312')

    @api.multi
    def initialize_task_forecast(self):
        new_forecast = []
        for rec in self:
            if rec.employee_id:
                unit_rate = rec.employee_id.timesheet_cost
                wbs = rec.account_project_id
                prev_date = 0
                current_forecast_dates = self.env['project.task.forecast'].search_read([('task_id', '=', rec.id),
                                                                                        ('forecast_type', '=', 'forecast')], ['date'])
                seen = set()
                for line in current_forecast_dates:
                    fdate = line['date'].strftime('%Y-%m-%d')
                    if fdate not in seen:
                        seen.add(fdate)
                seen = list(seen)
                # Todo: Change range for something we can add into a widget form populated by the user
                for i in range(0, 13):
                    date = (pd.Timestamp.now() + MonthBegin(i)).strftime('%Y-%m-%d')
                    vals = {
                        'task_id': rec.id,
                        'date': date,
                        'unit_rate': unit_rate,
                        'analytic_project_id': wbs.id,
                        'forecast_type': 'forecast',
                        'comment': 'evosoft_initialization'
                    }
                    if not prev_date == date and date not in seen:
                        new_forecast_line = self.env['project.task.forecast'].create(vals)
                    prev_date = date

            if rec.po_id:
                unit_rate = 1
                wbs = rec.account_project_id
                prev_date = 0
                current_forecast_dates = self.env['project.task.forecast'].search_read([('task_id', '=', rec.id),
                                                                                        ('forecast_type', '=', 'forecast')], ['date'])
                seen = set()
                for line in current_forecast_dates:
                    fdate = line['date'].strftime('%Y-%m-%d')
                    if fdate not in seen:
                        seen.add(fdate)
                seen = list(seen)
                # Todo: Change range for something we can add into a widget form populated by the user
                for i in range(0, 13):
                    date = (pd.Timestamp.now() + MonthBegin(i)).strftime('%Y-%m-%d')
                    vals = {
                        'task_id': rec.id,
                        'date': date,
                        'unit_rate': unit_rate,
                        'analytic_project_id': wbs.id,
                        'forecast_type': 'forecast',
                        'comment': 'evosoft_initialization'
                    }
                    if not prev_date == date and date not in seen:
                        new_forecast_line = self.env['project.task.forecast'].create(vals)
                    prev_date = date