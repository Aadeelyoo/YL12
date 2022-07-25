# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange

from odoo import models, fields, api
from odoo.addons.generic_grid.models.models import END_OF, STEP_BY, START_OF
from odoo.osv import expression


class AnalyticLine(models.Model):
    _inherit = 'project.task.forecast'


    '''
    amount = fields.Monetary(copy=False)
    '''
    is_timesheet = fields.Boolean(
        string="Employee Line",
        compute='_compute_is_timesheet', search='_search_is_timesheet',
        help="Set if this analytic line represents a line of timesheet.")
    '''
    task_id = fields.Many2one(group_expand='_read_group_task_ids')
    '''

    @api.multi
    @api.depends('project_id')
    def _compute_is_timesheet(self):
        for line in self:
            line.is_timesheet = bool(line.employee_id)

    def _search_is_timesheet(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('employee_id', '!=', False)]
        return [('employee_id', '=', False)]

    @api.model
    def _read_group_task_ids(self, tasks, domain, order):
        """ Display tasks with timesheet for the last grid period (defined from context) """
        if self.env.context.get('grid_anchor'):
            anchor = fields.Date.from_string(self.env.context['grid_anchor'])
        else:
            anchor = date.today() + relativedelta(weeks=-1, days=1, weekday=0)
        span = self.env.context.get('grid_range', 'week')
        date_ago = fields.Date.to_string(anchor - STEP_BY[span] + START_OF[span])

        tasks |= self.env['account.analytic.line'].search([
            ('user_id', '=', self.env.user.id),
            ('date', '>=', date_ago)
        ]).mapped('task_id')
        return tasks

    @api.multi
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        if column_field != 'date' or cell_field != 'quantity':
            raise ValueError(
                "{} can only adjust quantity (got {}) by date (got {})".format(
                    self._name,
                    cell_field,
                    column_field,
                ))

        additionnal_domain = self._get_adjust_grid_domain(column_value)
        domain = expression.AND([row_domain, additionnal_domain])
        line = self.search(domain)

        if len(line) > 1 or not line:
            # create new one
            day = column_value.split('/')[0]
            self.search(row_domain, limit=1).copy({
                'name': False,
                column_field: day,
                cell_field: change
            })

        else:  # update existing line
            line.write({
                cell_field: line[cell_field] + change
            })
        return

    def _get_adjust_grid_domain(self, column_value):
        # span is always daily and value is an iso range
        day = column_value.split('/')[0]
        return [('name', '=', False), ('date', '=', day)]

    @api.model
    def open_specific_forecast(self, type='forecast'):
        """
        The function will read the params passed in the url and return the forecast view with filtered values
        :param type: accept 'plan' or 'forecast'
        :return:
        """
        if 'params' in self.env.context:
            val_context = {}
            val_domain = []

            if type == 'forecast':
                val_domain.append(('forecast_type', '=', 'forecast'))
            if type == 'planned':
                val_domain.append(('forecast_type', '=', 'plan'))

            if 'internalref' in self.env.context['params']:
                internalref = self.env.context['params']['internalref']
                po_ids = self.env['purchase.order'].search([('internal_ref', 'ilike', internalref)])
                if len(po_ids) > 1:
                    val_domain.append(('po_id', 'in', po_ids.ids))
                if len(po_ids) == 1:
                    val_context.update({
                        'search_default_po_id': po_ids[0].id,
                    })

            if 'po_id' in self.env.context['params']:
                po_id = self.env.context['params']['po_id']
                po_ids = False
                if po_id == 'all':
                    po_ids = self.env['purchase.order'].search([])
                elif po_id == 'none':
                    val_domain.append(('po_id', '=', False))
                else:
                    po_ids = self.env['purchase.order'].search([('id', '=', po_id)])

                if po_ids:
                    if len(po_ids) > 1:
                        val_domain.append(('po_id', 'in', po_ids.ids))
                    if len(po_ids) == 1:
                        val_context.update({
                            'search_default_po_id': po_ids[0].id,
                        })

            if 'project_wbs' in self.env.context['params']:
                project_wbs = self.env.context['params']['project_wbs']
                wbs = self.env['account.analytic_wbs.project'].search([('name', 'ilike', project_wbs)])
                if len(wbs) > 1:
                    val_domain.append(('analytic_project_id', 'in', wbs.ids))
                if len(wbs) == 1:
                    val_context.update({
                        'search_default_analytic_project_id': wbs[0].id,
                    })

            if 'project_wbs_id' in self.env.context['params']:
                project_wbs_id = self.env.context['params']['project_wbs_id']
                wbs = self.env['account.analytic_wbs.project'].search([('id', '=', project_wbs_id)])
                if len(wbs) > 1:
                    val_domain.append(('analytic_project_id', 'in', wbs.ids))
                if len(wbs) == 1:
                    val_context.update({
                        'search_default_analytic_project_id': wbs[0].id,
                    })

            if 'project_code' in self.env.context['params']:
                project_code = self.env.context['params']['project_code']
                project_ids = self.env['project.project'].search([('project_code_id', 'ilike', project_code)])
                if len(project_ids) > 1:
                    val_domain.append(('project_id', 'in', project_ids.ids))
                if len(project_ids) == 1:
                    val_context.update({
                        'search_default_project_id': project_ids[0].id,
                    })
            if 'task_id' in self.env.context['params']:
                task_id = self.env.context['params']['task_id']
                if task_id == 'all':
                    exist_task_ids = self.env['project.task'].search([])
                    val_domain.append(('task_id', 'in', exist_task_ids.ids))
                else:
                    exist_task_id = self.env['project.task'].search([('id', '=', task_id)])
                    if exist_task_id:
                        val_domain.append(('task_id', '=', exist_task_id.id))

            if 'employee_id' in self.env.context['params']:
                employee_id = self.env.context['params']['employee_id']
                if employee_id == 'all':
                    exist_employee_ids = self.env['hr.employee'].search([])
                    val_domain.append(('employee_id', 'in', exist_employee_ids.ids))
                elif employee_id == 'none':
                    val_domain.append(('employee_id', '=', False))
                else:
                    exist_employee_id = self.env['hr.employee'].search([('id', '=', employee_id)])
                    if exist_employee_id:
                        val_domain.append(('employee_id', '=', exist_employee_id.id))

            if 'partner_id' in self.env.context['params']:
                partner_id = self.env.context['params']['partner_id']
                exist_partner_id = self.env['res.partner'].search([('id', '=', partner_id)])
                if exist_partner_id:
                    val_domain.append(('partner_id', '=', exist_partner_id.id))

            if 'month' in self.env.context['params']:
                month = self.env.context['params']['month']
                try:
                    dmonth = datetime.strptime(month, '%Y-%m')
                    r = monthrange(dmonth.year, dmonth.month)
                    startofmonth = datetime(dmonth.year, dmonth.month, 1)
                    endofmonth = datetime(dmonth.year, dmonth.month, r[1])
                    forecast_ids = self.env['project.task.forecast'].search([('date', '>=', startofmonth), ('date', '<=', endofmonth)])
                    if forecast_ids:
                       val_domain.append(('id', 'in', forecast_ids.ids))
                except ValueError:
                    pass

        res = self.env.ref('task_forecast_grid.open_view_all_task_forecast_pc_list').read()[0]
        if val_domain:
            res['domain'] = val_domain
        if val_context:
            res['context'] = val_context

        #print('val domain = %s' % val_domain)
        #print('val_context = %s' % val_context)
        return res