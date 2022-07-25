# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_cost_report_all_previous_incurred'
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
        CREATE OR REPLACE VIEW analytic_wbs_cost_report_all_previous_incurred AS 
        (
        SELECT *, row_number() OVER (ORDER BY rep_uid ASC) AS id
        FROM 
            (
            SELECT
                analytic_wbs_record_line.project_id AS project_id, 
                analytic_wbs_record_line.wbs_id AS wbs_id, 
                analytic_wbs_record_line.project_wbs_id AS project_wbs_id, 
                analytic_wbs_record_line.employee_id AS employee_id, 
                analytic_wbs_record_line.po_id AS po_id, 
                analytic_wbs_record_line.partner_id AS partner_id, 
                analytic_wbs_record_line.task_id AS task_id, 
                analytic_wbs_record_line.rep_uid AS rep_uid, 
                analytic_wbs_record_line.rep_name AS rep_name, 
                analytic_wbs_record_line.rep_uid_type AS rep_uid_type, 
                records.record_month AS data_col, 
                '42-Past Incurred' AS data_col_group, 
                analytic_wbs_record_line.variance AS amount
            FROM
                analytic_wbs_record_line
                INNER JOIN
                (
                    SELECT
                        analytic_wbs_record."id" AS record_id, 
                        analytic_wbs_record.report_period AS record_month
                    FROM
                        analytic_wbs_record
                        INNER JOIN
                        (
                            SELECT
                                analytic_wbs_record.project_id AS project_id
                            FROM
                                analytic_wbs_record
                            WHERE
                                analytic_wbs_record.record_type = 'mend' AND
                                analytic_wbs_record.is_active IS NOT NULL
                            GROUP BY
                                analytic_wbs_record.project_id
                        ) AS rec
                        ON 
                            analytic_wbs_record.project_id = rec.project_id
                    WHERE
                        analytic_wbs_record.is_active IS NOT NULL AND
                        analytic_wbs_record.record_type = 'mend'
                ) AS records
                ON 
                    analytic_wbs_record_line.record_id = records.record_id
            WHERE
                analytic_wbs_record_line.variance <> 0 AND
                analytic_wbs_record_line.data_col_group LIKE '%Incurred Total'
            ) AS summary
        )
        """
        self.env.cr.execute(query)

# CONCAT('Incurred ',records.record_month) AS data_col,