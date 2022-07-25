# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_commitment_current'
    _auto = False

    po_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)

    project_wbs_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS', readonly=True)
    wbs_id = fields.Many2one('account.analytic_wbs.account', string='WBS', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)

    task_id = fields.Many2one('project.task', string="Task", readonly=True)
    data_col = fields.Char(string='Data Type', readonly=True)
    data_col_group = fields.Char(string='Data Type Group', readonly=True)

    rep_uid = fields.Char(string='Rep UID', readonly=True)
    rep_name = fields.Char(string='Rep Name', readonly=True)
    rep_uid_type = fields.Char(string='Rep UID Type', readonly=True)

    amount = fields.Float(string='Total Amount', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        CREATE OR REPLACE VIEW analytic_wbs_commitment_current AS (
        SELECT *, row_number() OVER (ORDER BY rep_uid ASC) AS id
        FROM 
        (
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Actuals' AS data_col, 
                '30-Commitments' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'act'      
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type, 
                tci_analytic_project.tci_type
            UNION
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Open Commitments' AS data_col, 
                '30-Commitments' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'ocommit'     
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type, 
                tci_analytic_project.tci_type
            UNION
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Total' AS data_col, 
                '30-Commitments' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type IN ('act', 'ocommit')
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type
            UNION
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Outstanding CR' AS data_col, 
                '31-Change Requests' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'cr' 
                AND tci_analytic_project.is_outstanding 
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type, 
                tci_analytic_project.tci_type
            UNION
            
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Total Incurred' AS data_col, 
                '40-Incurred Total' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.is_outstanding
                AND tci_analytic_project.tci_type IN ('act', 'maccr', 'wt', 'inv')
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type, 
                tci_analytic_project.tci_type
            UNION
            SELECT
                project_task_forecast.project_id AS project_id, 
                project_task_forecast.account_id AS wbs_id, 
                project_task_forecast.analytic_project_id AS project_wbs_id, 
                project_task_forecast.employee_id AS employee_id, 
                project_task_forecast.po_id AS po_id, 
                project_task_forecast.partner_id AS partner_id, 
                project_task_forecast.task_id AS task_id, 
                project_task_forecast.rep_uid AS rep_uid, 
                project_task_forecast.rep_name AS rep_name, 
                CASE
                    WHEN project_task_forecast.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN project_task_forecast.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN project_task_forecast.rep_uid_type = 'task' THEN '04-Task'
                    WHEN project_task_forecast.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'EAC' AS data_col, 
                '65-EAC Total' AS data_col_group, 
                SUM(project_task_forecast.amount) AS amount
            FROM
                project_task_forecast
            WHERE
                project_task_forecast.forecast_type = 'forecast'
            GROUP BY
                project_task_forecast.project_id, 
                project_task_forecast.account_id, 
                project_task_forecast.analytic_project_id, 
                project_task_forecast.employee_id, 
                project_task_forecast.po_id, 
                project_task_forecast.partner_id, 
                project_task_forecast.task_id, 
                project_task_forecast.rep_uid, 
                project_task_forecast.rep_name, 
                project_task_forecast.rep_uid_type
            UNION
            SELECT
                tci_analytic_project.project_id AS project_id, 
                tci_analytic_project.account_id AS wbs_id, 
                tci_analytic_project.analytic_project_id AS project_wbs_id, 
                tci_analytic_project.employee_id AS employee_id, 
                tci_analytic_project.po_id AS po_id, 
                tci_analytic_project.partner_id AS partner_id, 
                tci_analytic_project.task_id AS task_id, 
                tci_analytic_project.rep_uid AS rep_uid, 
                tci_analytic_project.rep_name AS rep_name, 
                CASE
                    WHEN tci_analytic_project.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN tci_analytic_project.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN tci_analytic_project.rep_uid_type = 'task' THEN '04-Task'
                    WHEN tci_analytic_project.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'EAC' AS data_col, 
                '65-EAC Total' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.is_outstanding
                AND tci_analytic_project.tci_type IN ('act', 'maccr', 'wt', 'inv')
            GROUP BY
                tci_analytic_project.project_id, 
                tci_analytic_project.account_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.employee_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.task_id, 
                tci_analytic_project.rep_uid, 
                tci_analytic_project.rep_name, 
                tci_analytic_project.rep_uid_type, 
                tci_analytic_project.tci_type
            ) AS summary
        )
        """
        self.env.cr.execute(query)
