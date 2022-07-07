# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class TciHrEmployee(models.Model):

    _inherit = "hr.employee"
    tci_ids = fields.One2many('tci', 'employee_id', string='Actuals')

    task_ids = fields.One2many('project.task', 'employee_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task', string='Task Count')

    task_forecast_ids = fields.One2many('project.task.forecast', 'employee_id', string='Forecast Items',
                                        domain=[('forecast_type', '=', 'forecast')])
    task_forecast_count = fields.Integer(compute='_compute_forecast', string='Forecast Count')
    task_forecast_quantity = fields.Integer(compute='_compute_forecast', string='Forecast Quantity')
    task_forecast_amount = fields.Integer(compute='_compute_forecast', string='Forecast Amount')

    tci_analytic_project_ids = fields.One2many('tci.analytic.project', 'employee_id', string='Analytics')
    # todo: compute cost / amount
    # tci_analytic_project_amount = fields.Integer(compute='_compute_forecast', string='Forecast Amount')

    @api.multi
    def get_employee_id_from_name(self, name):
        employee_id = self.env['hr.employee'].search([('name', '=', name)], limit=1)
        if not employee_id:
            new_emp_val = {
                'name': name,
            }
            employee_id = self.env['hr.employee'].create(new_emp_val)
        return employee_id

    @api.multi
    def _compute_task(self):
        for record in self:
            record.task_count = len(record.task_ids)

    @api.multi
    def _compute_forecast(self):
        for record in self:
            record.task_forecast_count = len(record.task_forecast_ids)
            record.task_forecast_quantity = sum(line.quantity for line in record.task_forecast_ids)
            record.task_forecast_amount = round(sum(line.amount for line in record.task_forecast_ids), 2)

    # Todo: Modify the create task function to relate to employee and not PO
    @api.multi
    def create_task(self):
        for record in self:

            open_po_tci = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'ocommit')])
            project_wbs = self.env['tci.analytic.project'].search([('tci_id', 'in', open_po_tci.ids)])

            for project in record.project_ids:
                print(project)

                project_id = project.id
                project_wbs_ids = record.project_wbs_ids.search([('project_id', '=', project_id)])
                print(project_wbs_ids)

            for project_wbs in record.project_wbs_ids:
                project_id = project_wbs.project_id.id
                task_vals = {
                'name': 'Task One',
                'priority': '0',
                'kanban_state': 'normal',
                'po_id': record.id,
                'project_id': project_id,
                'account_project_id': project_wbs.id,
                'partner_id': record.partner_id.id,
                }
                new_task = self.env['project.task'].create(task_vals)

                # Create forecast for the new task based on open_po lines
                forecast_lines = []
                open_po_line_ids = self.env['tci.line'].search([('po_id', '=', record.id),
                                                                ('tci_type', '=', 'ocommit'),
                                                                ('analytic_project_id', '=', project_wbs.id)])
                for line in open_po_line_ids:
                    line.task_id = new_task.id
                    line_vals = {
                        'task_id': new_task.id,
                        'date': line.date,
                        'quantity': line.quantity,
                        'unit_rate': line.unit_amount,
                        'forecast_type': 'forecast',
                        'analytic_project_id': line.analytic_project_id.id,
                        'comment': line.description,
                    }
                    forecast_lines.append(line_vals)
                for forecast in forecast_lines:
                    self.env['project.task.forecast'].create(forecast)

    @api.multi
    def test_run_sql(self):
        print('test_run_sql')
        sql_query = '''
            SELECT
                purchase_order."id" AS po_id, 
                tci_analytic_project.analytic_project_id AS project_wbs
            FROM
                purchase_order
                INNER JOIN
                tci_analytic_project
                ON 
                    purchase_order."id" = tci_analytic_project.po_id
            GROUP BY
                purchase_order."id", 
                tci_analytic_project.analytic_project_id
            UNION
            SELECT
                purchase_order."id" AS po_id, 
                project_task_forecast.analytic_project_id AS project_wbs
            FROM
                purchase_order
                INNER JOIN
                project_task_forecast
                ON 
                    purchase_order."id" = project_task_forecast.po_id
            GROUP BY
                purchase_order."id", 
                project_task_forecast.analytic_project_id
            ORDER BY
                po_id ASC, 
                project_wbs ASC
        '''

        self._cr.execute(sql_query)

        po_model = self.env['purchase.order']
        result = {}

        for po_id, project_wbs in self.env.cr.fetchall():
            po = po_model.browse(po_id)
            wbs = self.env['account.analytic_wbs.project'].search(
                [('id', 'in', tuple(project_wbs))]
            )
            result[po] = wbs

        print(result)
        return result