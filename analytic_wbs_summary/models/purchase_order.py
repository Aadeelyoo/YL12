# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsSummaryPO(models.Model):
    _inherit = 'purchase.order'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="po_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryVendor(models.Model):
    _inherit = 'res.partner'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="partner_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryTask(models.Model):
    _inherit = 'project.task'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="task_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryWbs(models.Model):
    _inherit = 'account.analytic_wbs.account'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="wbs_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryProjectWbs(models.Model):
    _inherit = 'account.analytic_wbs.project'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="project_wbs_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryEmployee(models.Model):
    _inherit = 'hr.employee'

    wbs_summary_ids = fields.One2many(comodel_name="analytic_wbs_summary",
                                      inverse_name="employee_id", string="Summary Lines")
    wbs_summary_count = fields.Integer(string="Summary Count", compute="compute_wbs_summary_count")

    def compute_wbs_summary_count(self):
        for rec in self:
            rec.wbs_summary_count = len(rec.wbs_summary_ids)


class AnalyticWbsSummaryProjectTest(models.Model):
    _inherit = 'project.project'

    def test_function(self):
        self.compute_analytic_wbs_items()