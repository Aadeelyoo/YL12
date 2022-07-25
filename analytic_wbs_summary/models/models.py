# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_summary'
    _auto = False

    name = fields.Char(string='Name')
    date = fields.Date(string="Document Date", readonly=True)
    po_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)

    project_wbs_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS', readonly=True)
    wbs_id = fields.Many2one('account.analytic_wbs.account', string='WBS', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)

    quantity = fields.Float(string='Quantity', readonly=True)
    unit_rate = fields.Float(string='Unit Rate', readonly=True)
    amount = fields.Float(string='Total Amount', readonly=True)

    is_outstanding = fields.Boolean(string='Outstanding', readonly=True)
    task_id = fields.Many2one('project.task', string="Task", readonly=True)

    type = fields.Selection([
        ('act', 'Actuals'),
        ('ocommit', 'Open Commitment'),
        ('inv', 'Invoice'),
        ('wt', 'Work Ticket'),
        ('cr', 'Change Request'),
        ('maccr', 'Manual Accrual'),
        ('estimate', 'Estimate'),
        ('forecast', 'Forecast'),
    ], string='Type', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        CREATE OR REPLACE VIEW analytic_wbs_summary AS (
                    
        SELECT
            row_number() over(ORDER BY project_task_forecast.analytic_project_id) AS id,
            project_task_forecast.task_id AS task_id, 
            project_task_forecast.project_id AS project_id, 
            project_task_forecast.po_id AS po_id, 
            project_task_forecast.account_id AS wbs_id, 
            project_task_forecast.analytic_project_id AS project_wbs_id, 
            project_task_forecast.employee_id AS employee_id, 
            project_task_forecast.partner_id AS partner_id, 
            project_task_forecast.quantity AS quantity, 
            project_task_forecast.unit_rate AS unit_rate, 
            project_task_forecast.amount AS amount, 
            project_task_forecast.date AS date, 
            project_task_forecast.name AS name, 
            True AS is_outstanding,
            'forecast' AS type
        FROM
            project_task_forecast
        UNION
        SELECT
            row_number() over(ORDER BY tci_analytic_project.analytic_project_id) AS id,
            tci_analytic_project.task_id AS task_id, 
            tci_analytic_project.project_id AS project_id, 
            tci_analytic_project.po_id AS po_id, 
            tci_analytic_project.account_id AS wbs_id, 
            tci_analytic_project.analytic_project_id AS project_wbs_id, 
            tci_analytic_project.employee_id AS employee_id, 
            tci_analytic_project.partner_id AS partner_id, 
            tci_analytic_project.base AS quantity, 
            tci_analytic_project.base_allocation AS unit_rate,
            tci_analytic_project.amount AS amount, 
            tci_analytic_project.tci_date AS date, 
            tci_analytic_project."name" AS name, 
            True AS is_outstanding,
            tci_analytic_project.tci_type AS type
        FROM
            tci_analytic_project
        )
        """
        self.env.cr.execute(query)


