# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'analytic_wbs_cost_report'
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
    #data_type = fields.Char(string='Record Type', readonly=True)

    rep_uid = fields.Char(string='Rep UID', readonly=True)
    rep_name = fields.Char(string='Rep Name', readonly=True)
    rep_uid_type = fields.Char(string='Rep UID Type', readonly=True)

    amount = fields.Float(string='Amount', readonly=True)
    past_amount = fields.Float(string='Past Amount', readonly=True)
    variance = fields.Float(string='Variance', readonly=True)


    is_commitment_variant = fields.Boolean('Commitment Variant', compute='compute_is_commitment_variant', readonly=True,
                                           search='_search_is_com_variant')
    is_eac_variant = fields.Boolean('EAC Variant', compute='compute_is_eac_variant', readonly=True,
                                    search='_search_is_eac_variant')

    @api.model
    def _search_is_com_variant(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        res_ids = self.env['analytic_wbs_cost_report'].get_id_commitment_variance()
        return [('id', 'in', res_ids.ids)]

    def compute_is_commitment_variant(self):
        variant_recs = self.env['analytic_wbs_cost_report'].get_id_commitment_variance()
        for rec in self:
            if rec.id in variant_recs.ids:
                rec.is_commitment_variant = True
            else:
                rec.is_commitment_variant = False

    def get_id_commitment_variance(self):
        # find POs with variance
        analytic_lines_po = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '30-Commitments'),
                                                              ('data_col', '=', 'Total'),
                                                              ('po_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['po_id'])
        po_ids = set([line['po_id'][0] for line in analytic_lines_po])
        # find employee with variance
        analytic_lines_emp = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '30-Commitments'),
                                                              ('data_col', '=', 'Total'),
                                                              ('employee_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['employee_id'])
        employee_ids = set([line['employee_id'][0] for line in analytic_lines_emp])
        # find tasks with variance
        analytic_lines_task = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '30-Commitments'),
                                                              ('data_col', '=', 'Total'),
                                                              ('task_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['task_id'])
        task_ids = set([line['task_id'][0] for line in analytic_lines_task])
        search_domain = [
            '|', '|',
            ('po_id', 'in', tuple(po_ids)),
            ('employee_id', 'in', tuple(employee_ids)),
            ('task_id', 'in', tuple(task_ids)),
        ]

        res_ids = self.env['analytic_wbs_cost_report'].search(search_domain)
        return res_ids

    @api.model
    def _search_is_eac_variant(self, operator, value):
        if operator == 'like':
            operator = 'ilike'
        res_ids = self.env['analytic_wbs_cost_report'].get_id_eac_variance()
        return [('id', 'in', res_ids.ids)]

    def compute_is_eac_variant(self):
        variant_recs = self.env['analytic_wbs_cost_report'].get_id_eac_variance()
        for rec in self:
            if rec.id in variant_recs.ids:
                rec.is_eac_variant = True
            else:
                rec.is_eac_variant = False

    def get_id_eac_variance(self):
        # find POs with variance
        analytic_lines_po = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '65-EAC Total'),
                                                              ('data_col', '=', 'EAC'),
                                                              ('po_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['po_id'])
        po_ids = set([line['po_id'][0] for line in analytic_lines_po])
        # find employee with variance
        analytic_lines_emp = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '65-EAC Total'),
                                                              ('data_col', '=', 'EAC'),
                                                              ('employee_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['employee_id'])
        employee_ids = set([line['employee_id'][0] for line in analytic_lines_emp])
        # find tasks with variance
        analytic_lines_task = self.env['analytic_wbs_cost_report'].search_read([('data_col_group', '=', '65-EAC Total'),
                                                              ('data_col', '=', 'EAC'),
                                                              ('task_id', '!=', False),
                                                              ('variance', '!=', 0),
                                                              ], ['task_id'])
        task_ids = set([line['task_id'][0] for line in analytic_lines_task])
        search_domain = [
            '|', '|',
            ('po_id', 'in', tuple(po_ids)),
            ('employee_id', 'in', tuple(employee_ids)),
            ('task_id', 'in', tuple(task_ids)),
        ]

        res_ids = self.env['analytic_wbs_cost_report'].search(search_domain)
        return res_ids

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
                CREATE OR REPLACE VIEW analytic_wbs_cost_report AS 
                (
                    SELECT
                        summary.project_id AS project_id, 
                        summary.wbs_id AS wbs_id, 
                        summary.project_wbs_id AS project_wbs_id, 
                        summary.employee_id AS employee_id, 
                        summary.po_id AS po_id, 
                        summary.partner_id AS partner_id, 
                        summary.task_id AS task_id, 
                        summary.rep_uid AS rep_uid, 
                        summary.rep_name AS rep_name, 
                        summary.rep_uid_type AS rep_uid_type, 
                        summary.data_col AS data_col, 
                        summary.data_col_group AS data_col_group, 
                        SUM(summary.amount) AS amount, 
                        SUM(summary.past_amount) AS past_amount, 
                        SUM(summary.variance) AS variance, 
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
                            analytic_wbs_cost_report_current.amount AS amount, 
                            0 AS past_amount, 
                            0 AS variance
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
                            0 AS amount,
                            analytic_wbs_cost_report_previous.amount AS past_amount, 
                            0 AS variance
                        FROM
                            analytic_wbs_cost_report_previous
                        UNION
                        SELECT
                            analytic_wbs_cost_report_variance.project_id AS project_id, 
                            analytic_wbs_cost_report_variance.wbs_id AS wbs_id, 
                            analytic_wbs_cost_report_variance.project_wbs_id AS project_wbs_id, 
                            analytic_wbs_cost_report_variance.employee_id AS employee_id, 
                            analytic_wbs_cost_report_variance.po_id AS po_id, 
                            analytic_wbs_cost_report_variance.partner_id AS partner_id, 
                            analytic_wbs_cost_report_variance.task_id AS task_id, 
                            analytic_wbs_cost_report_variance.rep_uid AS rep_uid, 
                            analytic_wbs_cost_report_variance.rep_name AS rep_name, 
                            analytic_wbs_cost_report_variance.rep_uid_type AS rep_uid_type, 
                            analytic_wbs_cost_report_variance.data_col AS data_col, 
                            analytic_wbs_cost_report_variance.data_col_group AS data_col_group, 
                            0 AS amount, 
                            0 AS past_amount, 
                            analytic_wbs_cost_report_variance.amount AS variance
                        FROM
                            analytic_wbs_cost_report_variance
                        UNION
                        SELECT
                            analytic_wbs_cost_report_variance.project_id AS project_id, 
                            analytic_wbs_cost_report_variance.wbs_id AS wbs_id, 
                            analytic_wbs_cost_report_variance.project_wbs_id AS project_wbs_id, 
                            analytic_wbs_cost_report_variance.employee_id AS employee_id, 
                            analytic_wbs_cost_report_variance.po_id AS po_id, 
                            analytic_wbs_cost_report_variance.partner_id AS partner_id, 
                            analytic_wbs_cost_report_variance.task_id AS task_id, 
                            analytic_wbs_cost_report_variance.rep_uid AS rep_uid, 
                            analytic_wbs_cost_report_variance.rep_name AS rep_name, 
                            analytic_wbs_cost_report_variance.rep_uid_type AS rep_uid_type, 
                            'Incurred Current Period'  AS data_col, 
                            '50-Incurred Current' AS data_col_group, 
                            analytic_wbs_cost_report_variance.amount  AS amount, 
                            0 AS past_amount, 
                            0 AS variance
                        FROM
                            analytic_wbs_cost_report_variance
                        WHERE
                            analytic_wbs_cost_report_variance.data_col_group = '40-Incurred Total'
                        UNION
                        SELECT
                            analytic_wbs_cost_report_all_previous_incurred.project_id AS project_id, 
                            analytic_wbs_cost_report_all_previous_incurred.wbs_id AS wbs_id, 
                            analytic_wbs_cost_report_all_previous_incurred.project_wbs_id AS project_wbs_id, 
                            analytic_wbs_cost_report_all_previous_incurred.employee_id AS employee_id, 
                            analytic_wbs_cost_report_all_previous_incurred.po_id AS po_id, 
                            analytic_wbs_cost_report_all_previous_incurred.partner_id AS partner_id, 
                            analytic_wbs_cost_report_all_previous_incurred.task_id AS task_id, 
                            analytic_wbs_cost_report_all_previous_incurred.rep_uid AS rep_uid, 
                            analytic_wbs_cost_report_all_previous_incurred.rep_name AS rep_name, 
                            analytic_wbs_cost_report_all_previous_incurred.rep_uid_type AS rep_uid_type, 
                            analytic_wbs_cost_report_all_previous_incurred.data_col AS data_col, 
                            analytic_wbs_cost_report_all_previous_incurred.data_col_group AS data_col_group, 
                            analytic_wbs_cost_report_all_previous_incurred.amount AS amount,
                            0 AS past_amount, 
                            0 AS variance
                        FROM
                            analytic_wbs_cost_report_all_previous_incurred
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
                )
                """

        self.env.cr.execute(query)

