# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime
from datetime import date
from datetime import timedelta
from odoo.osv import osv


class project_analytic_wbs_account_line_timesheet(models.Model):

    _inherit = "account.analytic.line"
    analytic_wbs_project_id = fields.Many2one('account.analytic_wbs.project', string='wbs', required=False)
    line_comment = fields.Char(string='Comment')
    analytic_wbs_infocode_tags = fields.Many2many('account.analytic_wbs.infocode_tag', 'account_analytic_line_cc_infocode_rel', 'code', string='Infocode', help="Optional tags you may want to assign for custom reporting")
    #project_multiunit_id = fields.Many2one('project.project_multiunit', string='Multi Unit', required=False)
    infocode = fields.Selection([
        ('HC', 'HC'),
        ('RW', 'RW'),
    ], string='Info-Code')
    is_timesheet = fields.Boolean(string="Is a Timesheet")


    '''
    @api.onchange('analytic_wbs_project_id')
    def onchange_analytic_wbs_project_id(self):
        res = {}
        if self.analytic_wbs_project_id:
            ids = self.analytic_wbs_project_id.project_id.multiunit_ids.mapped('id')
            print(ids)
            res['domain'] = {
                'project_multiunit_id': [('id', 'in', ids)]}
            return res
    '''

    @api.onchange('analytic_wbs_project_id')
    def update_analytic(self):
        if self.analytic_wbs_project_id:
            self.account_id = self.analytic_wbs_project_id.project_id.analytic_account_id
            self.name = 'Timesheet Entry'

    @api.model
    def _calc_yesterday(self):
        res = fields.Date.to_string(date.today() - timedelta(days=1))
        return res


class project_analytic_wbs_timesheet(models.Model):

    _inherit = "account.analytic_wbs.project"
    account_analytic_line_ids = fields.Many2one('account.analytic.line', string='Analytic Line', required=False)




