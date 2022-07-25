# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, exceptions, _


class AnalyticWbsRecordLine(models.Model):
    _name = 'analytic.wbs.record.line'

    record_id = fields.Many2one('analytic.wbs.record', string='Report Id', readonly=False, ondelete='cascade')
    po_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)

    project_wbs_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS', readonly=True)
    wbs_id = fields.Many2one('account.analytic_wbs.account', string='WBS', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)

    task_id = fields.Many2one('project.task', string="Task", readonly=True)
    data_col = fields.Char(string='Data Type', readonly=True)
    data_col_group = fields.Char(string='Data Type Group', readonly=True)
    data_type = fields.Char(string='Record Type', readonly=False)

    record_data_timeline = fields.Selection([
        ('current', 'Current Record'),
        ('past', 'Past Report Record'),
    ], string='Record Timeline', default='current')

    rep_uid = fields.Char(string='Rep UID', readonly=False)
    rep_name = fields.Char(string='Rep Name', readonly=False)
    rep_uid_type = fields.Char(string='Rep UID Type', readonly=False)

    amount = fields.Float(string='Total Amount', readonly=True)
    past_amount = fields.Float(string='Past Amount', readonly=True)
    variance = fields.Float(string='Variance', readonly=False)


class AnalyticWbsRecord(models.Model):
    _name = 'analytic.wbs.record'
    _order = 'report_end_period desc'

    name = fields.Char(string='Name')
    report_end_period = fields.Date(string='Period End Date')
    report_period = fields.Char(string='Report Period', compute='_get_report_month', store=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    record_line_ids = fields.One2many('analytic.wbs.record.line', 'record_id', string='Report Lines')

    is_active = fields.Boolean('Active', default=True)
    record_type = fields.Selection([
        ('mend', 'Month End'),
        ('temp', 'Temporary Record'),
        ('baseline', 'Baseline Record'),
    ], string='Record Type', help="Type is used to group the records in the reports.", required=True)

    @api.depends('report_end_period')
    def _get_report_month(self):
        for rec in self:
            rec.report_period = rec.report_end_period.strftime('%Y-%m')


class AnalyticWbsRecord(models.Model):
    _inherit = 'project.project'

    analytic_wbs_record_ids = fields.One2many('analytic.wbs.record', 'project_id', string='Project Recordings')

    analytic_wbs_record_ids_mend = fields.One2many(comodel_name='analytic.wbs.record',
                                                   inverse_name='project_id',
                                                   # compute='_compute_records',
                                                   domain=[('record_type', '=', 'mend')],
                                                   string='Month End Records')

    analytic_wbs_record_ids_temp = fields.One2many(comodel_name='analytic.wbs.record',
                                                   inverse_name='project_id',
                                                   # compute='_compute_records',
                                                   domain=[('record_type', '=', 'temp')],
                                                   string='Temporary Records')

    analytic_wbs_record_ids_baseline = fields.One2many(comodel_name='analytic.wbs.record',
                                                       inverse_name='project_id',
                                                       # compute='_compute_records',
                                                       domain=[('record_type', '=', 'baseline')],
                                                       string='Baseline Records')
