# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_cost_report_current'
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
        CREATE OR REPLACE VIEW analytic_wbs_cost_report_current AS (
        SELECT *, row_number() OVER (ORDER BY rep_uid ASC) AS id
        FROM 
        (
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
                project_task_forecast.date_y_m AS data_col, 
                '60-Forecast' AS data_col_group, 
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
                rep_uid_type, 
                project_task_forecast.date_y_m
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
                'ETC Contingency' AS data_col, 
                '61-Forecast Total' AS data_col_group, 
                "sum"(project_task_forecast.amount_etc_contingency) AS amount
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
                rep_uid_type
            UNION
            SELECT
                account_analytic_wbs_budget_line.project_id AS project_id, 
                account_analytic_wbs_budget_line.account_id AS wbs_id, 
                account_analytic_wbs_budget_line.account_project_id AS project_wbs_id, 
                account_analytic_wbs_budget_line.employee_id AS employee_id, 
                account_analytic_wbs_budget_line.po_id AS po_id, 
                account_analytic_wbs_budget_line.partner_id AS partner_id, 
                account_analytic_wbs_budget_line.task_id AS task_id, 
                account_analytic_wbs_budget_line.rep_uid AS rep_uid, 
                account_analytic_wbs_budget_line.rep_name AS rep_name, 
                CASE
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'task' THEN '04-Task'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                CASE
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'baseline' THEN 'Budget'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'transfer' THEN 'Transfer'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'trend' THEN 'Cont. Trend Change'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'change' THEN 'Scope Change'
                    ELSE 'budget_transaction_calss not defined' END AS data_col, 
                '10-Budget' AS data_col_group, 
                SUM(account_analytic_wbs_budget_line.amount) AS amount
            FROM
                account_analytic_wbs_budget_line
            WHERE
                account_analytic_wbs_budget_line.bdgt_transaction_state = 'posted'
            GROUP BY
                account_analytic_wbs_budget_line.project_id, 
                account_analytic_wbs_budget_line.account_id, 
                account_analytic_wbs_budget_line.account_project_id, 
                account_analytic_wbs_budget_line.employee_id, 
                account_analytic_wbs_budget_line.po_id, 
                account_analytic_wbs_budget_line.partner_id, 
                account_analytic_wbs_budget_line.task_id, 
                account_analytic_wbs_budget_line.rep_uid, 
                account_analytic_wbs_budget_line.rep_name, 
                account_analytic_wbs_budget_line.rep_uid_type,
                account_analytic_wbs_budget_line.bdgt_transaction_class
            UNION
            SELECT
                account_analytic_wbs_budget_line.project_id AS project_id, 
                account_analytic_wbs_budget_line.account_id AS wbs_id, 
                account_analytic_wbs_budget_line.account_project_id AS project_wbs_id, 
                account_analytic_wbs_budget_line.employee_id AS employee_id, 
                account_analytic_wbs_budget_line.po_id AS po_id, 
                account_analytic_wbs_budget_line.partner_id AS partner_id, 
                account_analytic_wbs_budget_line.task_id AS task_id, 
                account_analytic_wbs_budget_line.rep_uid AS rep_uid, 
                account_analytic_wbs_budget_line.rep_name AS rep_name, 
                CASE
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'task' THEN '04-Task'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                CASE
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'baseline' THEN 'Budget'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'transfer' THEN 'Transfer'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'trend' THEN 'Cont. Trend Change'
                    WHEN account_analytic_wbs_budget_line.bdgt_transaction_class = 'change' THEN 'Scope Change'
                    ELSE 'budget_transaction_calss not defined' END AS data_col, 
                '15-Pending Budget Transactions' AS data_col_group, 
                SUM(account_analytic_wbs_budget_line.amount) AS amount
            FROM
                account_analytic_wbs_budget_line
            WHERE
                account_analytic_wbs_budget_line.bdgt_transaction_state <> 'posted'
            GROUP BY
                account_analytic_wbs_budget_line.project_id, 
                account_analytic_wbs_budget_line.account_id, 
                account_analytic_wbs_budget_line.account_project_id, 
                account_analytic_wbs_budget_line.employee_id, 
                account_analytic_wbs_budget_line.po_id, 
                account_analytic_wbs_budget_line.partner_id, 
                account_analytic_wbs_budget_line.task_id, 
                account_analytic_wbs_budget_line.rep_uid, 
                account_analytic_wbs_budget_line.rep_name, 
                account_analytic_wbs_budget_line.rep_uid_type,
                account_analytic_wbs_budget_line.bdgt_transaction_class
            UNION   
            SELECT
                account_analytic_wbs_budget_line.project_id AS project_id, 
                account_analytic_wbs_budget_line.account_id AS wbs_id, 
                account_analytic_wbs_budget_line.account_project_id AS project_wbs_id, 
                account_analytic_wbs_budget_line.employee_id AS employee_id, 
                account_analytic_wbs_budget_line.po_id AS po_id, 
                account_analytic_wbs_budget_line.partner_id AS partner_id, 
                account_analytic_wbs_budget_line.task_id AS task_id, 
                account_analytic_wbs_budget_line.rep_uid AS rep_uid, 
                account_analytic_wbs_budget_line.rep_name AS rep_name, 
                CASE
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'task' THEN '04-Task'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Bdgt. Work' AS data_col, 
                '12-Working Budget' AS data_col_group, 
                SUM(account_analytic_wbs_budget_line.total_amount) AS amount
            FROM
                account_analytic_wbs_budget_line
            WHERE
                account_analytic_wbs_budget_line.bdgt_transaction_state = 'posted'
            GROUP BY
                account_analytic_wbs_budget_line.project_id, 
                account_analytic_wbs_budget_line.account_id, 
                account_analytic_wbs_budget_line.account_project_id, 
                account_analytic_wbs_budget_line.employee_id, 
                account_analytic_wbs_budget_line.po_id, 
                account_analytic_wbs_budget_line.partner_id, 
                account_analytic_wbs_budget_line.task_id, 
                account_analytic_wbs_budget_line.rep_uid, 
                account_analytic_wbs_budget_line.rep_name, 
                account_analytic_wbs_budget_line.rep_uid_type
            UNION
            SELECT
                account_analytic_wbs_budget_line.project_id AS project_id, 
                account_analytic_wbs_budget_line.account_id AS wbs_id, 
                account_analytic_wbs_budget_line.account_project_id AS project_wbs_id, 
                account_analytic_wbs_budget_line.employee_id AS employee_id, 
                account_analytic_wbs_budget_line.po_id AS po_id, 
                account_analytic_wbs_budget_line.partner_id AS partner_id, 
                account_analytic_wbs_budget_line.task_id AS task_id, 
                account_analytic_wbs_budget_line.rep_uid AS rep_uid, 
                account_analytic_wbs_budget_line.rep_name AS rep_name, 
                CASE
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'task' THEN '04-Task'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Bdgt. Work No Ctgcy' AS data_col, 
                '12-Working Budget' AS data_col_group, 
                SUM(account_analytic_wbs_budget_line.amount) AS amount
            FROM
                account_analytic_wbs_budget_line
            WHERE
                account_analytic_wbs_budget_line.bdgt_transaction_state = 'posted'
            GROUP BY
                account_analytic_wbs_budget_line.project_id, 
                account_analytic_wbs_budget_line.account_id, 
                account_analytic_wbs_budget_line.account_project_id, 
                account_analytic_wbs_budget_line.employee_id, 
                account_analytic_wbs_budget_line.po_id, 
                account_analytic_wbs_budget_line.partner_id, 
                account_analytic_wbs_budget_line.task_id, 
                account_analytic_wbs_budget_line.rep_uid, 
                account_analytic_wbs_budget_line.rep_name, 
                account_analytic_wbs_budget_line.rep_uid_type
            UNION   
            SELECT
                account_analytic_wbs_budget_line.project_id AS project_id, 
                account_analytic_wbs_budget_line.account_id AS wbs_id, 
                account_analytic_wbs_budget_line.account_project_id AS project_wbs_id, 
                account_analytic_wbs_budget_line.employee_id AS employee_id, 
                account_analytic_wbs_budget_line.po_id AS po_id, 
                account_analytic_wbs_budget_line.partner_id AS partner_id, 
                account_analytic_wbs_budget_line.task_id AS task_id, 
                account_analytic_wbs_budget_line.rep_uid AS rep_uid, 
                account_analytic_wbs_budget_line.rep_name AS rep_name, 
                CASE
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'emp' THEN '02-Employees'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'po' THEN '03-Purchase Orders'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'task' THEN '04-Task'
                    WHEN account_analytic_wbs_budget_line.rep_uid_type = 'other' THEN '01-Others'
                    ELSE 'rep_uid_type not defined' END AS rep_uid_type, 
                'Contingency Allocation' AS data_col, 
                '12-Working Budget' AS data_col_group, 
                SUM(account_analytic_wbs_budget_line.contingency) AS amount
            FROM
                account_analytic_wbs_budget_line
            WHERE
                account_analytic_wbs_budget_line.bdgt_transaction_state = 'posted'
            GROUP BY
                account_analytic_wbs_budget_line.project_id, 
                account_analytic_wbs_budget_line.account_id, 
                account_analytic_wbs_budget_line.account_project_id, 
                account_analytic_wbs_budget_line.employee_id, 
                account_analytic_wbs_budget_line.po_id, 
                account_analytic_wbs_budget_line.partner_id, 
                account_analytic_wbs_budget_line.task_id, 
                account_analytic_wbs_budget_line.rep_uid, 
                account_analytic_wbs_budget_line.rep_name, 
                account_analytic_wbs_budget_line.rep_uid_type
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
                'ETC' AS data_col, 
                '61-Forecast Total' AS data_col_group, 
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
                'Invoices' AS data_col, 
                '35-Accruals' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'inv'
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
                'LEMs' AS data_col, 
                '35-Accruals' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'wt'
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
                'Others' AS data_col, 
                '35-Accruals' AS data_col_group,
                SUM(tci_analytic_project.amount) AS amount
            FROM
                tci_analytic_project 
            WHERE
                tci_analytic_project.tci_type = 'maccr'
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
