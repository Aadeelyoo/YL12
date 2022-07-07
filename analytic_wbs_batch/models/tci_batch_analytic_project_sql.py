# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummary(models.Model):
    _name = 'tci_batch_analytic_project_sql'
    _auto = False

    #ci_batch_id = fields.Many2one('tci.batch', string='Batch', readonly=True)
    batch_id = fields.Many2one('tci.batch', string='Batch', readonly=True)
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    amount = fields.Monetary(string='Total Amount', readonly=True)
    project_id = fields.Many2one('project.project', readonly=True)
    po_id = fields.Many2one('purchase.order', readonly=True)
    po_internal_ref = fields.Char(related='po_id.internal_ref', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    account_id = fields.Many2one('account.analytic_wbs.account', string='WBS Account', readonly=True)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        CREATE OR REPLACE VIEW tci_batch_analytic_project_sql AS (
        SELECT *, row_number() OVER (ORDER BY batch_id ASC) AS id
        FROM 
        (
            SELECT
                tci.batch_id AS batch_id, 
                tci_analytic_project.project_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.currency_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.po_internal_ref, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.account_id, 
                sum(tci_analytic_project.amount) AS amount
            FROM
                tci_batch
                INNER JOIN
                tci
                ON 
                    tci_batch."id" = tci.batch_id
                INNER JOIN
                tci_analytic_project
                ON 
                    tci."id" = tci_analytic_project.tci_id
            GROUP BY
                tci.batch_id, 
                tci_analytic_project.project_id, 
                tci_analytic_project.analytic_project_id, 
                tci_analytic_project.currency_id, 
                tci_analytic_project.po_id, 
                tci_analytic_project.po_internal_ref, 
                tci_analytic_project.partner_id, 
                tci_analytic_project.account_id
            ) AS summary
        )
        """
        self.env.cr.execute(query)
