# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning



class analytic_wbs_sap(models.Model):
    _inherit = 'account.analytic_wbs.account'

    @api.multi
    def get_wbs_account(self, code):
        wbs_account_id = self.search([('code', '=', code), ])
        if wbs_account_id:
            return wbs_account_id
        else:
            return False


class analytic_wbs_project_sap(models.Model):
    _inherit = 'account.analytic_wbs.project'

    sap_actuals_mapped_ids = fields.One2many('sap.actuals_line_mapped', 'account_project_id', string='Actual Lines')
    actual_count = fields.Integer("Actuals Count", compute='_compute_actual_count')

    # Computed SAP Money Values Fields
    @api.multi
    def _compute_sap_amt(self):
        sap_actuals_obj = self.env['sap.actuals_line_mapped']
        domain = [('account_project_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        sap_amounts = sap_actuals_obj.search_read(domain, ['account_project_id', 'val_ca_area_crcy'])
        account_project_ids = set([line['account_project_id'][0] for line in sap_amounts])
        data_debit_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for sap_amt in sap_amounts:
            if sap_amt['val_ca_area_crcy'] < 0.0:
                data_debit_amt[sap_amt['account_project_id'][0]] += sap_amt['val_ca_area_crcy']
            else:
                data_credit_amt[sap_amt['account_project_id'][0]] += sap_amt['val_ca_area_crcy']

        for rec in self:
            rec.sap_amt_debit = abs(data_debit_amt.get(rec.id, 0.0))
            rec.sap_amt_credit = data_credit_amt.get(rec.id, 0.0)
            rec.sap_amt_balance = rec.sap_amt_credit - rec.sap_amt_debit

    sap_amt_balance = fields.Monetary(compute='_compute_sap_amt', string='SAP Actuals')
    sap_amt_debit = fields.Monetary(compute='_compute_sap_amt', string='Actuals Debit')
    sap_amt_credit = fields.Monetary(compute='_compute_sap_amt', string='Actuals Credit')

    @api.multi
    def _compute_actual_count(self):
        for rec in self:
            rec.actual_count = len(rec.sap_actuals_mapped_ids)

    @api.multi
    def action_display_actuals(self):
        self.ensure_one()
        res = {
            'name': 'SAP Actuals',
            'type': 'ir.actions.act_window',
            'res_model': 'sap.actuals_line_mapped',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'limit': 80,
            'domain': [('account_project_id', '=', self.id)],
            'context': {
                'account_project_id': self.id,
                'default_account_project_id': self.id,
            },
        }
        return res

    @api.multi
    def get_project_wbs(self, code):
        wbs_project_id = self.search([('name', '=', code), ])
        if wbs_project_id:
            return wbs_project_id
        else:
            return False

    @api.multi
    def extract_wbs_info(self, code):
        if code:
            split_code = code.split('.')
            wbs_level = len(split_code)
            project_code = split_code[0]
            res = {}
            res['project'] = project_code
            wbs = project_code
            for i in range(1, wbs_level):
                wbs += str('.') + split_code[i]
                val = {
                    'name': wbs,
                    'code': split_code[i],
                }
                res[i] = val
        else:
            res = False
        return res

    @api.multi
    def create_project_wbs(self, val):
        #self.ensure_one()
        pid = val['project_id']
        wbs = val['wbs_id']
        new_pwbs = {
            'project_id': pid.id,
            'account_id': wbs.id,
            'project_account_type': 'active',
            'descr_short': wbs.descr_short,
            'name': pid.project_code_id + "." + wbs.name,
        }
        new_record = self.create(new_pwbs)
        if not new_record:
            raise Warning('New record not created - tell your administrator to investigate why this is happening')
        return new_record
