# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta, MO


class wbs_purchase_order(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order', 'tci.analytics']

    # project_id field to remove, po to be related to projects via po lines details
    project_id = fields.Many2one('project.project', string='Project', required=False, track_visibility='onchange')
    project_ids = fields.Many2many(relation='purchase_project_rel', comodel_name='project.project',
        column1='po_id', column2='project_id', readonly=True, compute='compute_project_ids')
    project_wbs_ids = fields.Many2many(relation='purchase_project_wbs_rel', comodel_name='account.analytic_wbs.project',
        column1='po_id', column2='project_wbs_id', readonly=True, compute='compute_project_wbs_ids')
    internal_ref = fields.Char(string='SAP Reference.', required=False)
    po_rev = fields.Integer(string='This PO Revision', readonly=True, default=0, copy=False)
    po_latest_rev = fields.Integer(string='Latest Revision', readonly=True, default=0, copy=False)
    parent_po_id = fields.Many2one('purchase.order', string='Main PO', readonly=True, copy=False)
    child_po_ids = fields.One2many('purchase.order', 'id', string='Child PO', readonly=True, ondelete='set null', copy=False)
    attachment_ids = fields.One2many(comodel_name="ir.attachment", inverse_name="res_id", compute="_compute_attachment",
        string="Attachment Files")
    attachment_number = fields.Integer(compute='_compute_attachment', string='Number of Attachments')

    tci_ids = fields.One2many('tci', 'po_id', string='TCI')
    # todo: to delete worktickets_ids field. Field replaced by wt_ids
    workticket_ids = fields.One2many('purchase.workticket', 'po_id', string='LEMs')

    wt_ids = fields.One2many('tci', 'po_id', string='LEMs', compute="_compute_tcis")
    wt_count = fields.Integer(compute='_compute_tcis', string='WT Count')
    cr_ids = fields.One2many('tci', 'po_id', string='Change Request', compute="_compute_tcis")
    cr_count = fields.Integer(compute='_compute_tcis', string='CR Count')
    inv_ids = fields.One2many('tci', 'po_id', string='Invoices', compute="_compute_tcis")
    inv_count = fields.Integer(compute='_compute_tcis', string='INV Count')
    commit_ids = fields.One2many('tci', 'po_id', string='Open Commitment', compute="_compute_tcis")
    commit_count = fields.Integer(compute='_compute_tcis', string='Commitment Count')
    ocommit_ids = fields.One2many('tci', 'po_id', string='Commitment', compute="_compute_tcis")
    ocommit_count = fields.Integer(compute='_compute_tcis', string='Open Commitment Count')
    maccr_ids = fields.One2many('tci', 'po_id', string='Manual Accruals', compute="_compute_tcis")
    maccr_count = fields.Integer(compute='_compute_tcis', string='Manual Accrual Count')

    template_ids = fields.One2many('tci.template', 'po_id', string='Templates', compute="_compute_tcis")
    template_count = fields.Integer(compute='_compute_tcis', string='Template Count')

    task_ids = fields.One2many('project.task', 'po_id', string='Tasks')
    task_count = fields.Integer(compute='_compute_task', string='Task Count')

    forecast_ids = fields.One2many('project.task.forecast', 'po_id', string='Forecast Lines')
    forecast_count = fields.Integer(compute='_compute_forecast', string='Forecast Count')

    tci_distribution_list = fields.Many2many(relation='purchase_partner_tci_distr_list_rel', comodel_name='res.partner',
                                             column1='po_id', column2='res_partner_id', readonly=False,
                                             domain=[('email', '!=', False)],
                                             string='Document Review Report Distribution')
    accrual_method = fields.Selection([
        ('po', 'Full PO Value, No Forecast'),
        ('pominusforecast', 'Full Po Value - Current Forecast')
        ], string='Accrual Method')

    @api.multi
    def compute_accruals_from_accrual_method(self):
        def read_summary(po_id):
            summary_obj = self.env["analytic.wbs.record.line_tree"]
            summary = summary_obj.search([('po_id', '=', po_id), ('data_col_group', 'in', ['40-Incurred-Total', '30-Commitments'])])

        for rec in self:
            if rec.accrual_method == 'po':
                print('po')
                # delete all forecast for the PO

                # Calculate current accruals (read from sql table)

                # create adjustment accruals for to match the po value

            if rec.accrual_method == 'pominusforecast':
                print('pominusforecast')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('partner_ref', operator, name), ('internal_ref', operator, name)]
        purchase_order_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return self.browse(purchase_order_ids).name_get()

    @api.one
    @api.depends('order_line.account_project_id')
    def compute_project_ids(self):
        project_grouped = []
        for record in self.mapped('order_line'):
            for project in record.account_project_id.project_id:
                if project.id not in project_grouped and project.id:
                    project_grouped.append(project.id)
        if project_grouped:
            self.project_ids = project_grouped

    @api.one
    @api.depends('order_line.account_project_id')
    def compute_project_wbs_ids(self):
        project_wbs_grouped = []
        for record in self.mapped('order_line'):
            for project_wbs in record.account_project_id:
                if project_wbs.id not in project_wbs_grouped and project_wbs.id:
                    project_wbs_grouped.append(project_wbs.id)
        if project_wbs_grouped:
            self.project_wbs_ids = project_wbs_grouped

    @api.multi
    def _compute_task(self):
        for record in self:
            record.task_count = len(record.task_ids)

    @api.multi
    def _compute_forecast(self):
        for record in self:
            record.forecast_count = len(record.forecast_ids)

    @api.multi
    def create_task(self):
        for record in self:

            open_po_tci = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'ocommit')])
            project_wbs = self.env['tci.analytic.project'].search([('tci_id', 'in', open_po_tci.ids)])

            for project in record.project_ids:
                print(project)

                project_id = project.id
                project_wbs_ids = record.project_wbs_ids.search([('project_id', '=', project_id)])
                print(project_wbs_ids)

            for project_wbs in record.project_wbs_ids:
                project_id = project_wbs.project_id.id
                task_vals = {
                'name': 'Task One',
                'priority': '0',
                'kanban_state': 'normal',
                'po_id': record.id,
                'project_id': project_id,
                'account_project_id': project_wbs.id,
                'partner_id': record.partner_id.id,
                }
                new_task = self.env['project.task'].create(task_vals)

                # Create forecast for the new task based on open_po lines
                forecast_lines = []
                open_po_line_ids = self.env['tci.line'].search([('po_id', '=', record.id),
                                                                ('tci_type', '=', 'ocommit'),
                                                                ('analytic_project_id', '=', project_wbs.id)])
                for line in open_po_line_ids:
                    line.task_id = new_task.id
                    line_vals = {
                        'task_id': new_task.id,
                        'date': line.date,
                        'quantity': line.quantity,
                        'unit_rate': line.unit_amount,
                        'analytic_project_id': line.analytic_project_id.id,
                        'comment': line.description,
                    }
                    forecast_lines.append(line_vals)
                for forecast in forecast_lines:
                    self.env['project.task.forecast'].create(forecast)


    @api.multi
    def _compute_tcis(self):
        for record in self:
            tci_obj = self.env['tci'].search([('po_id', '=', record.id)])
            record.wt_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'wt')]).ids
            record.wt_count = len(record.wt_ids)
            record.cr_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'cr')]).ids
            record.cr_count = len(record.cr_ids)
            record.inv_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'inv')]).ids
            record.inv_count = len(record.inv_ids)
            record.commit_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', 'in', ('open_commit', 'act'))]).ids
            record.commit_count = len(record.commit_ids)
            record.ocommit_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'open_commit')]).ids
            record.ocommit_count = len(record.ocommit_ids)
            record.maccr_ids = self.env['tci'].search([('po_id', '=', record.id), ('tci_type', '=', 'maccr')]).ids
            record.maccr_count = len(record.maccr_ids)
            record.template_ids = self.env['tci.template'].search([('po_id', '=', record.id)]).ids
            record.template_count = len(record.template_ids)

    @api.multi
    def _compute_attachment(self):
        for record in self:
            record.attachment_ids = self.env['ir.attachment'].search(
                [('res_model', '=', 'purchase.order'), ('res_id', '=', record.id)]).ids
            record.attachment_number = len(record.attachment_ids)

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'purchase.order'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'purchase.order', 'default_res_id': self.id}
        return res

    @api.multi
    def create_po_rev(self, default=None):
        if not self.po_rev:
            new_rev = self.po_latest_rev + 1
            new_parent_id = self.id
            new_rev_name = "{}-Rev{}".format(self.name,new_rev)

            new_po = super(wbs_purchase_order, self).copy(default=default)
            for line in new_po.order_line:
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id, quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order[:10], uom_id=line.product_uom)
                line.date_planned = line._get_date_planned(seller)

            new_po.name = new_rev_name
            new_po.parent_po_id = new_parent_id
            new_po.po_rev = new_rev

            for record in self.child_po_ids:
                record.po_latest_rev = new_rev

            return new_po

    @api.model
    def create(self, vals):
        record = super(wbs_purchase_order, self).create(vals)
        if not record.po_rev:
            record.parent_po_id = record.id
        return record

    @api.multi
    def action_view_workticket(self):
        '''
        This function returns an action that display existing vendor work ticket of given purchase order ids.
        '''
        action = self.env.ref('analytic_wbs.act_purchase_workticket_all')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'search_default_po_id': self.id, 'default_po_id': self.id}

        return result

    workticket_count = fields.Float(compute='compute_workticket_count', string='Workticket Count')

    @api.multi
    def compute_workticket_count(self):
        for purchase in self:
            purchase.workticket_count = len(purchase.workticket_ids)

    # Re-define the default name depends function
    @api.multi
    @api.depends('name', 'partner_ref', 'internal_ref')
    def name_get(self):
        result = []
        for po in self:
            name = po.name
            if po.internal_ref:
                name += ' ['+po.internal_ref+']'
            if po.partner_ref:
                name += ' ('+po.partner_ref+')'
            result.append((po.id, name))
        return result

    @api.multi
    def action_display_wt(self):
        self.ensure_one()
        res = {
            'name': 'LEMs',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id), ('tci_type', '=', 'wt')],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
                'default_tci_type': 'wt',
            },
        }
        return res

    @api.multi
    def action_display_cr(self):
        self.ensure_one()
        res = {
            'name': 'Change Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id), ('tci_type', '=', 'cr')],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
                'default_tci_type': 'cr',
            },
        }
        return res

    @api.multi
    def action_display_inv(self):
        self.ensure_one()
        res = {
            'name': 'Workflow Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id), ('tci_type', '=', 'inv')],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
                'search_default_group_status': True,
                'default_tci_type': 'inv',
            },
        }
        return res

    @api.multi
    def action_display_maccr(self):
        self.ensure_one()
        res = {
            'name': 'Manual Accruals',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id), ('tci_type', '=', 'maccr')],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
                'default_tci_type': 'maccr',
            },
        }
        return res

    @api.multi
    def action_display_commit(self):
        self.ensure_one()
        res = {
            'name': 'Commitments',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id), ('tci_type', 'in', ('ocommit', 'act'))],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
                'search_default_group_type': 1,
            },
        }
        return res

    @api.multi
    def action_po_templates(self):
        self.ensure_one()
        res = {
            'name': 'TCI Templates',
            'type': 'ir.actions.act_window',
            'res_model': 'tci.template',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id)],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
            },
        }
        return res

    @api.multi
    def action_display_task(self):
        self.ensure_one()
        res = {
            'name': 'Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 40,
            'domain': [('po_id', '=', self.id)],
            'context': {
                'po_id': self.id,
                'default_po_id': self.id,
            },
        }
        return res

    @api.multi
    def create_po_tasks(self):
        for record in self:
            for wbs in record.project_wbs_ids:
                #search for existing task with the wbs under this PO
                task_exist = self.env['project.task'].search([('account_project_id', '=', wbs.id), ('po_id', '=', record.id)])
                if not task_exist:
                    name = str(record.name) + " - " + str(wbs.name)
                    start_date = record.date_order
                    date_end = start_date + relativedelta(months=1)
                    self.etc_distr_calc_type = 'uniform'
                    vals = {
                        'po_id': record.id,
                        'name': name,
                        'project_id': wbs.project_id.id,
                        'etc_distr_calc_type': ('%s' % self.etc_distr_calc_type),
                        'etc_distr_date_start': start_date,
                        'etc_distr_date_end': date_end,
                        'etc_distr_calc_interval_size': 'month',
                        'auto_forecast_calc': True,
                        'account_project_id': wbs.id,
                        'etc_amount_calc_type': 'po_cr',
                    }
                    #print(vals)
                    new_task = self.env['project.task'].create(vals)
                    #print(new_task)
                    new_task.get_etc_distribution()


class wbs_purchase_order_line(models.Model):

    _inherit = "purchase.order.line"
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', ondelete='restrict',
        states={
            'draft': [('required', False)],
            'pending': [('required', False)],
            'submitted': [('required', True)],
            'rejected': [('required', False)]})
    project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
    po_rev_ref = fields.Integer(string='PO Revision', readonly=True, default=0)

    '''
    @api.onchange('account_project_id')
    def onchange_account_project(self):
        res = {}
        if self.order_id:
            if self.order_id.project_id:
                ids = self.order_id.project_id.analytic_wbs_project_ids.mapped('id')
                res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res
    '''