# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_cost_report_variance'
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
            CREATE OR REPLACE VIEW analytic_wbs_cost_report_variance AS 
            (
                SELECT 
                    summary.project_id,
                    summary.wbs_id,
                    summary.project_wbs_id,
                    summary.employee_id,
                    summary.po_id,
                    summary.partner_id,
                    summary.task_id,
                    summary.rep_uid,
                    summary.rep_name,
                    summary.rep_uid_type,
                    summary.data_col,
                    summary.data_col_group,
                    CAST(SUM(summary.amount) AS DECIMAL (250,2)) AS amount,
                    row_number() OVER (ORDER BY rep_uid ASC) AS id
                FROM 
                    (
                    SELECT
                        analytic_wbs_cost_report_current.project_id AS project_id, 
                        analytic_wbs_cost_report_current.wbs_id AS wbs_id, 
                        analytic_wbs_cost_report_current.project_wbs_id AS project_wbs_id, 
                        analytic_wbs_cost_report_current.employee_id AS employee_id, 
                        analytic_wbs_cost_report_current.po_id AS po_id, 
                        analytic_wbs_cost_report_current.partner_id AS partner_id, 
                        analytic_wbs_cost_report_current.task_id AS task_id, 
                        analytic_wbs_cost_report_current.rep_uid AS rep_uid, 
                        analytic_wbs_cost_report_current.rep_name AS rep_name, 
                        analytic_wbs_cost_report_current.rep_uid_type AS rep_uid_type, 
                        analytic_wbs_cost_report_current.data_col AS data_col, 
                        analytic_wbs_cost_report_current.data_col_group AS data_col_group, 
                        analytic_wbs_cost_report_current.amount AS amount
                    FROM
                        analytic_wbs_cost_report_current
                    UNION
                    SELECT
                        analytic_wbs_cost_report_previous.project_id AS project_id, 
                        analytic_wbs_cost_report_previous.wbs_id AS wbs_id, 
                        analytic_wbs_cost_report_previous.project_wbs_id AS project_wbs_id, 
                        analytic_wbs_cost_report_previous.employee_id AS employee_id, 
                        analytic_wbs_cost_report_previous.po_id AS po_id, 
                        analytic_wbs_cost_report_previous.partner_id AS partner_id, 
                        analytic_wbs_cost_report_previous.task_id AS task_id, 
                        analytic_wbs_cost_report_previous.rep_uid AS rep_uid, 
                        analytic_wbs_cost_report_previous.rep_name AS rep_name, 
                        analytic_wbs_cost_report_previous.rep_uid_type AS rep_uid_type, 
                        analytic_wbs_cost_report_previous.data_col AS data_col, 
                        analytic_wbs_cost_report_previous.data_col_group AS data_col_group, 
                        (analytic_wbs_cost_report_previous.amount * -1) AS amount
                    FROM
                        analytic_wbs_cost_report_previous
                    ) AS summary
                GROUP BY
                    summary.project_id,
                    summary.wbs_id,
                    summary.project_wbs_id,
                    summary.employee_id,
                    summary.po_id,
                    summary.partner_id,
                    summary.task_id,
                    summary.rep_uid,
                    summary.rep_name,
                    summary.rep_uid_type,
                    summary.data_col,
                    summary.data_col_group
                HAVING
                    SUM(amount) <> 0
            )
            """
        self.env.cr.execute(query)
