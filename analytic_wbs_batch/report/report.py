# -*- coding:utf-8 -*-


from odoo import api, models, fields


class TciBatchReport(models.AbstractModel):
    _name = 'report.analytic_wbs_batch.tci_batch_lem_report_id'

    def get_tci_ids(self, res_id):
        if res_id:
            tci_ids = self.env['tci'].search([('batch_id', '=', res_id.id)])
            return tci_ids

    def get_analytic_ids(self, res_id):
        if res_id:
            analytic_ids = self.env['tci_batch_analytic_project_sql'].search([('batch_id', '=', res_id.id)])
            return analytic_ids

    def get_approval_ids(self, res_id):
        if res_id:
            mail_apporvers = self.env['mail.approvers'].search([('res_model', '=', 'tci.batch'), ('res_id', '=', res_id.id)])
            return mail_apporvers


    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['tci.batch'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'tci.batch',
            'docs': docs,
            'get_tci_ids': self.get_tci_ids,
            'get_analytic_ids': self.get_analytic_ids,
            'get_approval_ids': self.get_approval_ids
        }
