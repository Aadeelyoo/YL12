# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class account_analytic_wbs_tag(models.Model):
    _name = 'account.analytic_wbs.tag'
    _description = 'wbs Tags'
    name = fields.Char(string='wbs Tag', index=True, required=True)
    color = fields.Integer('Color Index')


class account_analytic_wbs_infocode_tag(models.Model):
    _name = 'account.analytic_wbs.infocode_tag'
    _description = 'wbs Info Code Tag'
    short_descr = fields.Char(string='Description', required=True)
    name = fields.Char(string='Code', index=True, required=True)
    color = fields.Integer('Color Index')

    def name_get(self):
        result = {}
        for record in self.browse():
            result[record.id] = record.name + " " + record.short_descr

        return result.items()


FIELDS_TO_MONITOR_ZERO_BALANCE = [
    "posted_baseline_bdgt_amt_balance",
    "posted_change_bdgt_amt_balance",
    "posted_bdgt_amt_balance",
    "posted_contingency_amt_balance",
    "actual_balance",
    "open_commit_balance",
    "commit_balance",
    "cr_out_balance",
    "inv_out_balance",
    "wt_out_balance",
    "maccr_balance",
    "incur_balance",
    "etc_balance",
    "eac",
    "contingency_spent",
]

class account_analytic_wbs_account(models.Model):
    _name = 'account.analytic_wbs.account'
    _inherit = ['mail.thread', 'tci.analytics']
    _description = 'wbs Account'
    _order = 'code, name asc'

    @api.multi
    def _compute_debit_credit_balance(self):
        analytic_wbs_project_obj = self.env['account.analytic_wbs.project']
        domain = [('account_id', 'in', self.mapped('id'))]

        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_amounts = analytic_wbs_project_obj.search_read(domain, ['account_id', 'balance'])

        account_ids = set([line['account_id'][0] for line in account_amounts])
        #initialize values
        data_debit = {account_id: 0.0 for account_id in account_ids}
        data_credit = {account_id: 0.0 for account_id in account_ids}
        for account_amount in account_amounts:
            if account_amount['balance'] < 0.0:
                data_debit[account_amount['account_id'][0]] += account_amount['balance']
            else:
                data_credit[account_amount['account_id'][0]] += account_amount['balance']

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

    name = fields.Char(string='wbs Account', index=True, required=True, track_visibility='onchange')
    #company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    #currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    _sql_constraints = [
        ('name', 'unique(name)', 'Please enter Unique Name for the company WBS'),
    ]
    descr_short = fields.Char(string='Label', index=True, required=True)
    description = fields.Char(string='Description', index=True, required=False)
    comment = fields.Char(string='Comment', index=True)
    code = fields.Char(string='Code', index=True, track_visibility='onchange')
    analytic_wbs_uom = fields.Many2one('uom.uom', string='UOM', required=False)
    analytic_wbs_level = fields.Integer(string='WBS Level', required=False)
    # FIXME: we reused account_type to implement the closed accounts (feature removed by mistake on release of v9) without modifying the schemas on already released v9, but it would be more clean to rename it
    account_type = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived')
        ], string='State', required=True, default='active')

    tag_ids = fields.Many2many('account.analytic_wbs.tag', 'account_analytic_wbs_account_tag_rel', 'account_id', 'tag_id', string='Tags', copy=True)
    line_ids = fields.One2many('account.analytic_wbs.progress_line', 'account_project_id', string="wbs Projects")

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True)
    is_active = fields.Boolean('Active', index=True, default=True)

    is_old_wbs = fields.Boolean(string='Is Old WBS')

    # Computed Money Values Fields
    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Balance')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit')

    @api.multi
    def _compute_debit_credit_balance_qty(self):
        analytic_wbs_project_obj = self.env['account.analytic_wbs.project']
        domain = [('account_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_qty_amounts = analytic_wbs_project_obj.search_read(domain, ['account_id', 'balance_qty'])
        account_ids = set([line['account_id'][0] for line in account_qty_amounts])
        data_debit_qty = {account_id: 0.0 for account_id in account_ids}
        data_credit_qty = {account_id: 0.0 for account_id in account_ids}
        for account_qty_amount in account_qty_amounts:
            if account_qty_amount['balance_qty'] < 0.0:
                data_debit_qty[account_qty_amount['account_id'][0]] += account_qty_amount['balance_qty']
            else:
                data_credit_qty[account_qty_amount['account_id'][0]] += account_qty_amount['balance_qty']

        for account in self:
            account.debit_qty = abs(data_debit_qty.get(account.id, 0.0))
            account.credit_qty = data_credit_qty.get(account.id, 0.0)
            account.balance_qty = account.credit_qty - account.debit_qty

    # Computed Quantity Values Fields
    balance_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Balance Qty')
    debit_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Debit Qty')
    credit_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Credit Qty')

    @api.multi
    def _compute_debit_credit_balance_mhr(self):
        analytic_wbs_project_obj = self.env['account.analytic_wbs.project']
        domain = [('account_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_mhr_amounts = analytic_wbs_project_obj.search_read(domain, ['account_id', 'balance_mhr'])
        account_ids = set([line['account_id'][0] for line in account_mhr_amounts])
        data_debit_mhr = {account_id: 0.0 for account_id in account_ids}
        data_credit_mhr = {account_id: 0.0 for account_id in account_ids}
        for account_mhr_amount in account_mhr_amounts:
            if account_mhr_amount['balance_mhr'] < 0.0:
                data_debit_mhr[account_mhr_amount['account_id'][0]] += account_mhr_amount['balance_mhr']
            else:
                data_credit_mhr[account_mhr_amount['account_id'][0]] += account_mhr_amount['balance_mhr']

        for account in self:
            account.debit_mhr = abs(data_debit_mhr.get(account.id, 0.0))
            account.credit_mhr = data_credit_mhr.get(account.id, 0.0)
            account.balance_mhr = account.credit_mhr - account.debit_mhr

    # Computed Man Hours Values Fields
    balance_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Balance Mhr')
    debit_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Debit Mhr')
    credit_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Credit Mhr')

    @api.multi
    def name_get(self):
        res = []
        for analytic_wbs in self:
            name = analytic_wbs.name
            if analytic_wbs.code:
                name = '['+analytic_wbs.code+'] '+name
            if analytic_wbs.partner_id:
                name = name +' - '+analytic_wbs.partner_id.commercial_partner_id.name
            res.append((analytic_wbs.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(account_analytic_wbs_account, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        partners = self.env['res.partner'].search([('name', operator, name)], limit=limit)
        if partners:
            domain = ['|'] + domain + [('partner_id', 'in', partners.ids)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class wbs_res_partner(models.Model):

    _name = "res.partner"
    _inherit = ['res.partner', 'tci.analytics']

    po_ids = fields.One2many('purchase.order', 'partner_id', string='Purchase Order')


class project_analytic_wbs(models.Model):
    _name = "project.project"
    _inherit = ['project.project', 'tci.analytics']

    analytic_wbs_project_ids = fields.One2many('account.analytic_wbs.project', 'project_id', string='wbs', domain=[('zero_balance', '=', False)])
    analytic_wbs_line_transaction_ids = fields.One2many('account.analytic_wbs.progress_transaction', 'project_id', string='Progress')
    #multiunit_ids = fields.One2many('project.project_multiunit', 'project_id', string='Units')
    budget_transaction_ids = fields.One2many('account.analytic_wbs.budget_transaction', 'project_id', string='Budget')
    #sow_transaction_ids = fields.One2many('account.analytic_wbs.sow_transaction', 'project_id', string='SOW')
    forecast_transaction_ids = fields.One2many('account.analytic_wbs.forecast_transaction', 'project_id', string='Forecast')
    _sql_constraints = [
        ('project_code_id', 'unique(project_code_id)', 'Please enter Unique Project Code'),
    ]
    purchase_order_ids = fields.Many2many(relation='purchase_project_rel', comodel_name='purchase.order', column2='po_id', column1='project_id', string='Purchasse Order')

    po_ids = fields.One2many(comodel_name='purchase.order', compute='compute_analytic_wbs_items')
    po_count = fields.Float(compute='compute_po_count', string='PO Count')

    tci_ids = fields.Many2many(comodel_name='tci', string='TCI')

    wt_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')
    act_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')
    inv_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')
    cr_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')
    ocommit_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')
    maccr_ids = fields.One2many(comodel_name='tci', compute='compute_analytic_wbs_items')

    old_wbs = fields.Boolean(string='Use old WBS', default=False)

    #tci_count = fields.Float(compute='compute_tci_count', string='TCI Count')

    def compute_analytic_wbs_items(self):
        for rec in self:
            # get the list of project_wbs
            project_wbs_ids = rec.analytic_wbs_project_ids.ids

            #get po_ids from forecast model
            po_list_forecast_model = self.env['project.task.forecast'].search_read([('analytic_project_id', 'in', project_wbs_ids), ('po_id', '!=', False)], ['po_id'])
            pos = set([line['po_id'][0] for line in po_list_forecast_model])
            po_ids = set(pos)

            # get po_ids from purchasse_order model
            po_list_po_model = self.env['purchase.order.line'].search_read(
                [('account_project_id', 'in', project_wbs_ids), ('order_id', '!=', False)], ['order_id'])
            pos2 = set([line['order_id'][0] for line in po_list_po_model])
            po_ids.update(pos2)

            # get po_ids from tci model
            po_list_tci_model = self.env['tci.line'].search_read(
                [('analytic_project_id', 'in', project_wbs_ids), ('po_id', '!=', False)], ['po_id'])
            pos3 = set([line['po_id'][0] for line in po_list_tci_model])
            po_ids.update(pos3)

            if po_ids:
                rec.purchase_order_ids = [(6, 0, po_ids)]
                rec.po_ids = [(6, 0, po_ids)]

            # Get All TCI assigned to the project
            list_tci_model = self.env['tci.line'].search_read(
                [('analytic_project_id', 'in', project_wbs_ids)], ['tci_id'])

            tci_ids = set([line['tci_id'][0] for line in list_tci_model])
            if tci_ids:
                rec.tci_ids = [(6, 0, tci_ids)]

            # Get All Forecast assigned to the project
            list_tci_model = self.env['tci.line'].search_read(
                [('analytic_project_id', 'in', project_wbs_ids)], ['tci_id'])

            tci_ids = set([line['tci_id'][0] for line in list_tci_model])

            if tci_ids:
                rec.tci_ids = [(6, 0, tci_ids)]

            wt = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'wt')])
            rec.wt_ids = wt.ids

            act = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'act')])
            rec.act_ids = act.ids

            cr = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'cr')])
            rec.cr_ids = cr.ids

            inv = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'inv')])
            rec.inv_ids = inv.ids

            ocommit = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'ocommit')])
            rec.ocommit_ids = ocommit.ids

            maccr = self.env['tci'].search([('id', 'in', list(tci_ids)), ('tci_type', '=', 'maccr')])
            rec.maccr_ids = maccr.ids

    @api.multi
    def compute_po_count(self):
        for project in self:
            project.po_count = len(project.purchase_order_ids)

    workticket_ids = fields.One2many('purchase.workticket', 'project_id', string='Work Ticket')
    workticket_count = fields.Float(compute='compute_workticket_count', string='Work Ticket Count')

    @api.multi
    def compute_workticket_count(self):
        for project in self:
            project.workticket_count = len(project.workticket_ids)

    @api.multi
    def action_view_project_wt(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_wt')
        result = action.read()[0]
        print(result)
        #override the context to get rid of the default filtering
        result['context'] = {'default_tci_type': 'wt', 'search_default_active': 1}
        result['domain'] = [('tci_type', '=', 'wt'), ('id', 'in', self.wt_ids.ids)]
        # Get po_ids related to self.id
        po_ids = self.po_ids.ids
        vals = {
            'po_id_domain': po_ids,
        }
        result['context'].update(vals)
        print(result)
        return result

    @api.multi
    def action_view_project_po(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('purchase.purchase_form_action')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('id', 'in', self.po_ids.ids)]

        return result

    @api.multi
    def action_view_project_act(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_act')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('tci_type', '=', 'act'), ('id', 'in', self.act_ids.ids)]
        return result

    @api.multi
    def action_view_project_ocommit(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_open_commit')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('tci_type', '=', 'ocommit'), ('id', 'in', self.ocommit_ids.ids)]
        return result

    @api.multi
    def action_view_project_inv(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_inv')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('tci_type', '=', 'inv'), ('id', 'in', self.inv_ids.ids)]
        return result

    @api.multi
    def action_view_project_maccr(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_maccr')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('tci_type', '=', 'maccr'), ('id', 'in', self.maccr_ids.ids)]
        return result

    @api.multi
    def action_view_project_cr(self):
        '''
        This function returns an action that display existing vendor purchase orders of a given project id.
        '''
        action = self.env.ref('analytic_wbs.action_pc_tci_cr')
        result = action.read()[0]
        #override the context to get rid of the default filtering
        result['domain'] = [('tci_type', '=', 'cr'), ('id', 'in', self.cr_ids.ids)]
        return result

'''
class project_multiunit(models.Model):
    _name = 'project.project_multiunit'
    _description = 'Project Multi Unit'
    short_descr = fields.Char(string='Description', required=False)
    name = fields.Char(string='Code', index=True, required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    unit_type_id = fields.Many2one('project.project_multiunit.type', 'Unit Type', required=False)
    account_analytic_line_ids = fields.One2many('account.analytic.line', 'project_multiunit_id', string='Unit')

    def name_get(self, cr, uid, ids, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = record.name + " " + record.short_descr

        return result.items()


class project_multiunit_type(models.Model):
    _name = 'project.project_multiunit.type'
    _description = 'Project Multi Unit Type'
    short_descr = fields.Char(string='Description', required=False)
    name = fields.Char(string='Code', index=True, required=True)
    project_multiunit_ids = fields.One2many('project.project_multiunit', 'unit_type_id', string='Unit')
'''


class account_analytic_wbs_project(models.Model):
    _name = 'account.analytic_wbs.project'
    _description = 'wbs Project'
    _inherit = ['mail.thread', 'tci.analytics']
    _order = 'name asc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Project wbs', required=True)

    _sql_constraints = [
        ('name', 'unique(name)', 'Please enter Unique Name for the project wbs'),
    ]

    descr_short = fields.Char(string='Description', index=True, required=True)
    comment = fields.Char(string='Comment', index=True)
    date = fields.Date('Created Date', required=False, index=True, default=fields.Date.context_today)
    account_id = fields.Many2one('account.analytic_wbs.account', 'wbs Account', required=True, ondelete='restrict', index=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    uom_id = fields.Many2one(related="account_id.analytic_wbs_uom", string="UOM", readonly=True)
    is_active = fields.Boolean('Active', index=True, default=True)
    # company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    # currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    task_ids = fields.One2many(comodel_name='project.task', inverse_name='account_project_id', string='Task')
    task_ids_employee = fields.One2many(comodel_name='project.task',
                                        inverse_name='account_project_id',
                                        # compute='_compute_task',
                                        domain=[('employee_id', '!=', False)],
                                        string='Employee Tasks')

    task_ids_po = fields.One2many(comodel_name='project.task',
                                  inverse_name='account_project_id',
                                  # compute='_compute_task',
                                  domain=[('po_id', '!=', False)],
                                  string='PO Tasks')
    task_ids_other = fields.One2many(comodel_name='project.task',
                                     inverse_name='account_project_id',
                                     # compute='_compute_task',
                                     domain=[('po_id', '=', False), ('employee_id', '=', False)],
                                     string='Other Tasks')

    forecast_ids = fields.One2many(comodel_name='project.task.forecast',
                                   inverse_name='analytic_project_id',
                                   domain=[('forecast_type', '=', 'forecast')],
                                   string='Task Forecast')

    budget_ids = fields.One2many(comodel_name='account.analytic_wbs.budget_line',
                                 inverse_name='account_project_id',
                                 string='Budget Lines')

    project_account_type = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived')
    ], string='State', required=True, default='active')

    @api.onchange('account_id','project_id')
    def update_name(self):
        if self.account_id and self.project_id:
            self.name = self.project_id.project_code_id + "." + self.account_id.name
            self.descr_short = self.account_id.descr_short

    #Make sure analytic_account is selected only once
    @api.onchange('project_id')
    def onchange_project(self):
        res = {}
        project_no = self.project_id.name
        existing_ids = self.env['account.analytic_wbs.project'].search([('project_id', '=', project_no)]).mapped('account_id.id')

        if self.project_id:
            all_ids = self.env['account.analytic_wbs.account'].search([('account_type', '=', 'active')]).mapped('id')
            ids = [x for x in all_ids if x not in existing_ids]
            res['domain'] = {'account_id': [('id', 'in', ids)]}
        return res

    @api.multi
    def _compute_task(self):
        for rec in self:
            emp_task = self.env['project.task'].search([('account_project_id', '=', rec.id), ('employee_id', '!=', False)])
            po_task = self.env['project.task'].search([('account_project_id', '=', rec.id), ('po_id', '!=', False)])
            other_task = self.env['project.task'].search([('account_project_id', '=', rec.id),
                                                          ('po_id', '=', False), ('employee_id', '=', False)])
            rec.task_ids_employee = emp_task.ids
            rec.task_ids_po = po_task.ids
            rec.task_ids_other = other_task.ids


    @api.multi
    def _compute_debit_credit_balance_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [
            ('account_project_id', 'in', self.mapped('id')),
              ]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount['qty_amount']
            else:
                data_credit_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount['qty_amount']

        for account in self:
            account.debit_qty = abs(data_debit_qty.get(account.id, 0.0))
            account.credit_qty = data_credit_qty.get(account.id, 0.0)
            account.balance_qty = account.credit_qty - account.debit_qty

    # Computed Quantity Values Fields
    balance_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Claimed Qty')
    debit_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Debit Qty')
    credit_qty = fields.Float(compute='_compute_debit_credit_balance_qty', string='Credit Qty')

    @api.multi
    def _compute_debit_credit_balance_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [('account_project_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.debit_mhr = abs(data_debit_mhr.get(account.id, 0.0))
            account.credit_mhr = data_credit_mhr.get(account.id, 0.0)
            account.balance_mhr = account.credit_mhr - account.debit_mhr

    # Computed Man Hours Values Fields
    balance_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Claimed Mhr')
    debit_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Debit Mhr')
    credit_mhr = fields.Float(compute='_compute_debit_credit_balance_mhr', string='Credit Mhr')

    @api.multi
    def _compute_debit_credit_balance(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [('account_project_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amounts])
        data_debit = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit = {account_project_id: 0.0 for account_project_id in account_project_ids}
        for account_project_amount in account_project_amounts:
            if account_project_amount['amount'] < 0.0:
                data_debit[account_project_amount['account_project_id'][0]] += account_project_amount[
                    'amount']
            else:
                data_credit[account_project_amount['account_project_id'][0]] += account_project_amount[
                    'amount']

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

    # Computed Money Values Fields
    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Claimed Amount')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit')

    # Calculate quantity for posted budget
    @api.multi
    def _compute_posted_budget_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount', 'bdgt_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_bdgt_qty_debit = abs(data_debit_bdgt_qty.get(account.id, 0.0))
            account.posted_bdgt_qty_credit = data_credit_bdgt_qty.get(account.id, 0.0)
            account.posted_bdgt_qty_balance = account.posted_bdgt_qty_credit - account.posted_bdgt_qty_debit

    posted_bdgt_qty_balance = fields.Float(compute='_compute_posted_budget_qty', string='Budget Qty')
    posted_bdgt_qty_debit = fields.Float(compute='_compute_posted_budget_qty', string='Budget Qty Debit')
    posted_bdgt_qty_credit = fields.Float(compute='_compute_posted_budget_qty', string='Budget Qty Credit')

    # Calculate quantity for posted baseline budget
    @api.multi
    def _compute_posted_baseline_budget_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'baseline')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_baseline_bdgt_qty_debit = abs(data_debit_bdgt_qty.get(account.id, 0.0))
            account.posted_baseline_bdgt_qty_credit = data_credit_bdgt_qty.get(account.id, 0.0)
            account.posted_baseline_bdgt_qty_balance = account.posted_baseline_bdgt_qty_credit - account.posted_baseline_bdgt_qty_debit

    posted_baseline_bdgt_qty_balance = fields.Float(compute='_compute_posted_baseline_budget_qty', string='Budget Baseline Qty')
    posted_baseline_bdgt_qty_debit = fields.Float(compute='_compute_posted_baseline_budget_qty', string='Budget Baseline Qty Debit')
    posted_baseline_bdgt_qty_credit = fields.Float(compute='_compute_posted_baseline_budget_qty', string='Budget Baseline Qty Credit')

    # Calculate quantity for posted change budget
    @api.multi
    def _compute_posted_change_budget_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'change')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_bdgt_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_change_bdgt_qty_debit = abs(data_debit_bdgt_qty.get(account.id, 0.0))
            account.posted_change_bdgt_qty_credit = data_credit_bdgt_qty.get(account.id, 0.0)
            account.posted_change_bdgt_qty_balance = account.posted_change_bdgt_qty_credit - account.posted_change_bdgt_qty_debit

    posted_change_bdgt_qty_balance = fields.Float(compute='_compute_posted_change_budget_qty', string='Budget Change Qty')
    posted_change_bdgt_qty_debit = fields.Float(compute='_compute_posted_change_budget_qty', string='Budget Change Qty Debit')
    posted_change_bdgt_qty_credit = fields.Float(compute='_compute_posted_change_budget_qty', string='Budget Change Qty Credit')

    # Calculate man hours for posted budget
    @api.multi
    def _compute_posted_budget_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))
    
        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount',
                                                                                'bdgt_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
    
        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
    
        for account in self:
            account.posted_bdgt_mhr_debit = abs(data_debit_bdgt_mhr.get(account.id, 0.0))
            account.posted_bdgt_mhr_credit = data_credit_bdgt_mhr.get(account.id, 0.0)
            account.posted_bdgt_mhr_balance = account.posted_bdgt_mhr_credit - account.posted_bdgt_mhr_debit
    
    posted_bdgt_mhr_balance = fields.Float(compute='_compute_posted_budget_mhr', string='Budget mhr')
    posted_bdgt_mhr_debit = fields.Float(compute='_compute_posted_budget_mhr', string='Budget mhr Debit')
    posted_bdgt_mhr_credit = fields.Float(compute='_compute_posted_budget_mhr', string='Budget mhr Credit')

    # Calculate man hours for posted baseline budget
    @api.multi
    def _compute_posted_baseline_budget_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'baseline')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.posted_baseline_bdgt_mhr_debit = abs(data_debit_bdgt_mhr.get(account.id, 0.0))
            account.posted_baseline_bdgt_mhr_credit = data_credit_bdgt_mhr.get(account.id, 0.0)
            account.posted_baseline_bdgt_mhr_balance = account.posted_baseline_bdgt_mhr_credit - account.posted_baseline_bdgt_mhr_debit

    posted_baseline_bdgt_mhr_balance = fields.Float(compute='_compute_posted_baseline_budget_mhr', string='Budget Baseline mhr')
    posted_baseline_bdgt_mhr_debit = fields.Float(compute='_compute_posted_baseline_budget_mhr', string='Budget Baseline mhr Debit')
    posted_baseline_bdgt_mhr_credit = fields.Float(compute='_compute_posted_baseline_budget_mhr', string='Budget Baseline mhr Credit')

    # Calculate man hours for posted change budget
    @api.multi
    def _compute_posted_change_budget_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'change')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_bdgt_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.posted_change_bdgt_mhr_debit = abs(data_debit_bdgt_mhr.get(account.id, 0.0))
            account.posted_change_bdgt_mhr_credit = data_credit_bdgt_mhr.get(account.id, 0.0)
            account.posted_change_bdgt_mhr_balance = account.posted_change_bdgt_mhr_credit - account.posted_change_bdgt_mhr_debit

    posted_change_bdgt_mhr_balance = fields.Float(compute='_compute_posted_change_budget_mhr', string='Budget Change mhr')
    posted_change_bdgt_mhr_debit = fields.Float(compute='_compute_posted_change_budget_mhr', string='Budget Change mhr Debit')
    posted_change_bdgt_mhr_credit = fields.Float(compute='_compute_posted_change_budget_mhr', string='Budget Change mhr Credit')

    # Calculate amounts for posted budget
    @api.multi
    def _compute_posted_budget_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount',
                                                                                'bdgt_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_bdgt_amt_debit = abs(data_debit_bdgt_amt.get(account.id, 0.0))
            account.posted_bdgt_amt_credit = data_credit_bdgt_amt.get(account.id, 0.0)
            account.posted_bdgt_amt_balance = account.posted_bdgt_amt_credit - account.posted_bdgt_amt_debit

    posted_bdgt_amt_balance = fields.Monetary(compute='_compute_posted_budget_amt', string='Working Budget')
    posted_bdgt_amt_debit = fields.Monetary(compute='_compute_posted_budget_amt', string='Working Budget Debit')
    posted_bdgt_amt_credit = fields.Monetary(compute='_compute_posted_budget_amt', string='Working Budget Credit')

    # Calculate amounts for posted budget working budget with contingency
    @api.multi
    def _compute_posted_budget_work_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'total_amount',
                                                                                'bdgt_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['total_amount'] < 0.0:
                data_debit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'total_amount']
            else:
                data_credit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'total_amount']

        for account in self:
            account.posted_bdgt_work_amt_debit = abs(data_debit_bdgt_amt.get(account.id, 0.0))
            account.posted_bdgt_work_amt_credit = data_credit_bdgt_amt.get(account.id, 0.0)
            account.posted_bdgt_work_amt_balance = account.posted_bdgt_work_amt_credit - account.posted_bdgt_work_amt_debit

    posted_bdgt_work_amt_balance = fields.Monetary(compute='_compute_posted_budget_work_amt', string='Working Budget with Contingency')
    posted_bdgt_work_amt_debit = fields.Monetary(compute='_compute_posted_budget_work_amt', string='Working Budget with ctgcy Debit')
    posted_bdgt_work_amt_credit = fields.Monetary(compute='_compute_posted_budget_work_amt', string='Working Budget with ctgcy Credit')

    # Calculate baseline amounts for posted budget
    @api.multi
    def compute_posted_baseline_budget_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'baseline')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_baseline_bdgt_amt_debit = abs(data_debit_bdgt_amt.get(account.id, 0.0))
            account.posted_baseline_bdgt_amt_credit = data_credit_bdgt_amt.get(account.id, 0.0)
            account.posted_baseline_bdgt_amt_balance = account.posted_baseline_bdgt_amt_credit - account.posted_baseline_bdgt_amt_debit

    posted_baseline_bdgt_amt_balance = fields.Monetary(compute='compute_posted_baseline_budget_amt', string='Baseline Budget')
    posted_baseline_bdgt_amt_debit = fields.Monetary(compute='compute_posted_baseline_budget_amt', string='Baseline Budget Debit')
    posted_baseline_bdgt_amt_credit = fields.Monetary(compute='compute_posted_baseline_budget_amt', string='Baseline Budget Credit')

    # Calculate contingency for posted budget
    @api.multi
    def _compute_posted_contingency_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'contingency',
                                                                                'bdgt_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_contingency_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_contingency_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['contingency'] < 0.0:
                data_debit_contingency_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'contingency']
            else:
                data_credit_contingency_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'contingency']

        for account in self:
            account.posted_contingency_amt_debit = abs(data_debit_contingency_amt.get(account.id, 0.0))
            account.posted_contingency_amt_credit = data_credit_contingency_amt.get(account.id, 0.0)
            account.posted_contingency_amt_balance = account.posted_contingency_amt_credit - account.posted_contingency_amt_debit

    posted_contingency_amt_balance = fields.Monetary(compute='_compute_posted_contingency_amt', string='Contingency')
    posted_contingency_amt_debit = fields.Monetary(compute='_compute_posted_contingency_amt', string='Contingency Debit')
    posted_contingency_amt_credit = fields.Monetary(compute='_compute_posted_contingency_amt', string='Contingency Credit')

    @api.multi
    def _compute_contingency_spending(self):
        for record in self:
            record.contingency_spent = record.posted_bdgt_amt_balance - record.eac

    contingency_spent = fields.Monetary(compute='_compute_contingency_spending', string='EAC - Budget')
    zero_balance = fields.Boolean()
    zero_balance_computed = fields.Boolean(compute='_compute_zero_balance')

    @api.multi
    def _compute_zero_balance(self):
        for rec in self:
            rec.sudo().write({
                "zero_balance": False,
                "zero_balance_computed": False
            })
            fields_data = rec.read(FIELDS_TO_MONITOR_ZERO_BALANCE)[0]
            if "id" in fields_data:
                fields_data.pop("id")
            if all(fields_data[field] == 0 for field in fields_data):
                rec.sudo().write({
                    "zero_balance": True,
                    "zero_balance_computed": True
                })
    # Calculate baseline contingency for posted budget
    @api.multi
    def compute_posted_baseline_budget_contingency(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'), ('bdgt_transaction_class', '=', 'baseline')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_contingency_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'contingency'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_contingency_amounts])
        data_debit_bdgt_contingency = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_contingency = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_contingency_amount in account_project_contingency_amounts:
            if account_project_contingency_amount['contingency'] < 0.0:
                data_debit_bdgt_contingency[account_project_contingency_amount['account_project_id'][0]] += account_project_contingency_amount[
                    'contingency']
            else:
                data_credit_bdgt_contingency[account_project_contingency_amount['account_project_id'][0]] += account_project_contingency_amount[
                    'contingency']

        for account in self:
            account.posted_baseline_bdgt_contingency_debit = abs(data_debit_bdgt_contingency.get(account.id, 0.0))
            account.posted_baseline_bdgt_contingency_credit = data_credit_bdgt_contingency.get(account.id, 0.0)
            account.posted_baseline_bdgt_contingency_balance = account.posted_baseline_bdgt_contingency_credit - account.posted_baseline_bdgt_contingency_debit

    posted_baseline_bdgt_contingency_balance = fields.Monetary(compute='compute_posted_baseline_budget_contingency', string='Baseline Contingency')
    posted_baseline_bdgt_contingency_debit = fields.Monetary(compute='compute_posted_baseline_budget_contingency', string='Baseline Contingency Debit')
    posted_baseline_bdgt_contingency_credit = fields.Monetary(compute='compute_posted_baseline_budget_contingency', string='Baseline Contingency Credit')

    # Calculate change amounts for posted budget
    @api.multi
    def compute_posted_change_budget_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'),
                  ('bdgt_transaction_class', 'in', ('change', 'transfer', 'trend'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_bdgt_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_change_bdgt_amt_debit = abs(data_debit_bdgt_amt.get(account.id, 0.0))
            account.posted_change_bdgt_amt_credit = data_credit_bdgt_amt.get(account.id, 0.0)
            account.posted_change_bdgt_amt_balance = account.posted_change_bdgt_amt_credit - account.posted_change_bdgt_amt_debit

    posted_change_bdgt_amt_balance = fields.Monetary(compute='compute_posted_change_budget_amt', string='Budget Changes')
    posted_change_bdgt_amt_debit = fields.Monetary(compute='compute_posted_change_budget_amt', string='Budget Changes Debit')
    posted_change_bdgt_amt_credit = fields.Monetary(compute='compute_posted_change_budget_amt', string='Budget Changes Credit')

    # Calculate change contingency for posted budget
    @api.multi
    def compute_posted_change_budget_contingency(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.budget_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('bdgt_transaction_state', '=', 'posted'),
                  ('bdgt_transaction_class', 'in', ('change', 'transfer', 'trend'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_contingency_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'contingency'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_contingency_amounts])
        data_debit_bdgt_contingency = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_bdgt_contingency = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_contingency_amount in account_project_contingency_amounts:
            if account_project_contingency_amount['contingency'] < 0.0:
                data_debit_bdgt_contingency[account_project_contingency_amount['account_project_id'][0]] += account_project_contingency_amount[
                    'contingency']
            else:
                data_credit_bdgt_contingency[account_project_contingency_amount['account_project_id'][0]] += account_project_contingency_amount[
                    'contingency']

        for account in self:
            account.posted_change_bdgt_contingency_debit = abs(data_debit_bdgt_contingency.get(account.id, 0.0))
            account.posted_change_bdgt_contingency_credit = data_credit_bdgt_contingency.get(account.id, 0.0)
            account.posted_change_bdgt_contingency_balance = account.posted_change_bdgt_contingency_credit - account.posted_change_bdgt_contingency_debit

    posted_change_bdgt_contingency_balance = fields.Monetary(compute='compute_posted_change_budget_contingency', string='Change Budget')
    posted_change_bdgt_contingency_debit = fields.Monetary(compute='compute_posted_change_budget_contingency', string='Change Budget Debit')
    posted_change_bdgt_contingency_credit = fields.Monetary(compute='compute_posted_change_budget_contingency', string='Change Budget Credit')

    # Calculate quantity for posted forecast
    @api.multi
    def _compute_posted_forecast_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.forecast_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('forecast_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount',
                                                                                 'forecast_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_forecast_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_forecast_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_forecast_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_forecast_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_forecast_qty_debit = abs(data_debit_forecast_qty.get(account.id, 0.0))
            account.posted_forecast_qty_credit = data_credit_forecast_qty.get(account.id, 0.0)
            account.posted_forecast_qty_balance = account.posted_forecast_qty_credit - account.posted_forecast_qty_debit

    posted_forecast_qty_balance = fields.Float(compute='_compute_posted_forecast_qty', string='Forecast Qty')
    posted_forecast_qty_debit = fields.Float(compute='_compute_posted_forecast_qty', string='Forecast Qty Debit')
    posted_forecast_qty_credit = fields.Float(compute='_compute_posted_forecast_qty', string='Forecast Qty Credit')

    # Calculate man hours for posted forecast
    @api.multi
    def _compute_posted_forecast_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.forecast_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('forecast_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount',
                                                                                 'forecast_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_forecast_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_forecast_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_forecast_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_forecast_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.posted_forecast_mhr_debit = abs(data_debit_forecast_mhr.get(account.id, 0.0))
            account.posted_forecast_mhr_credit = data_credit_forecast_mhr.get(account.id, 0.0)
            account.posted_forecast_mhr_balance = account.posted_forecast_mhr_credit - account.posted_forecast_mhr_debit

    posted_forecast_mhr_balance = fields.Float(compute='_compute_posted_forecast_mhr', string='Forecast mhr')
    posted_forecast_mhr_debit = fields.Float(compute='_compute_posted_forecast_mhr', string='Forecast mhr Debit')
    posted_forecast_mhr_credit = fields.Float(compute='_compute_posted_forecast_mhr', string='Forecast mhr Credit')

    # Calculate amounts for posted forecast
    @api.multi
    def _compute_posted_forecast_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.forecast_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('forecast_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount',
                                                                                 'forecast_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_forecast_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_forecast_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_forecast_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_forecast_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_forecast_amt_debit = abs(data_debit_forecast_amt.get(account.id, 0.0))
            account.posted_forecast_amt_credit = data_credit_forecast_amt.get(account.id, 0.0)
            account.posted_forecast_amt_balance = account.posted_forecast_amt_credit - account.posted_forecast_amt_debit

    posted_forecast_amt_balance = fields.Monetary(compute='_compute_posted_forecast_amt', string='Forecast')
    posted_forecast_amt_debit = fields.Monetary(compute='_compute_posted_forecast_amt', string='Forecast Debit')
    posted_forecast_amt_credit = fields.Monetary(compute='_compute_posted_forecast_amt', string='Forecast Credit')

    # Calculate quantity for posted sow
    @api.multi
    def _compute_posted_sow_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.sow_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('sow_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount',
                                                                                 'sow_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_sow_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_sow_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_sow_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_sow_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_sow_qty_debit = abs(data_debit_sow_qty.get(account.id, 0.0))
            account.posted_sow_qty_credit = data_credit_sow_qty.get(account.id, 0.0)
            account.posted_sow_qty_balance = account.posted_sow_qty_credit - account.posted_sow_qty_debit

    posted_sow_qty_balance = fields.Float(compute='_compute_posted_sow_qty', string='Sow Qty')
    posted_sow_qty_debit = fields.Float(compute='_compute_posted_sow_qty', string='Sow Qty Debit')
    posted_sow_qty_credit = fields.Float(compute='_compute_posted_sow_qty', string='Sow Qty Credit')

    # Calculate man hours for posted sow
    @api.multi
    def _compute_posted_sow_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.sow_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('sow_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount',
                                                                                 'sow_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_sow_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_sow_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_sow_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_sow_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.posted_sow_mhr_debit = abs(data_debit_sow_mhr.get(account.id, 0.0))
            account.posted_sow_mhr_credit = data_credit_sow_mhr.get(account.id, 0.0)
            account.posted_sow_mhr_balance = account.posted_sow_mhr_credit - account.posted_sow_mhr_debit

    posted_sow_mhr_balance = fields.Float(compute='_compute_posted_sow_mhr', string='Sow mhr')
    posted_sow_mhr_debit = fields.Float(compute='_compute_posted_sow_mhr', string='Sow mhr Debit')
    posted_sow_mhr_credit = fields.Float(compute='_compute_posted_sow_mhr', string='Sow mhr Credit')

    # Calculate amounts for posted sow
    @api.multi
    def _compute_posted_sow_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.sow_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('sow_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount',
                                                                                 'sow_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_sow_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_sow_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_sow_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_sow_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_sow_amt_debit = abs(data_debit_sow_amt.get(account.id, 0.0))
            account.posted_sow_amt_credit = data_credit_sow_amt.get(account.id, 0.0)
            account.posted_sow_amt_balance = account.posted_sow_amt_credit - account.posted_sow_amt_debit

    posted_sow_amt_balance = fields.Monetary(compute='_compute_posted_sow_amt', string='Sow')
    posted_sow_amt_debit = fields.Monetary(compute='_compute_posted_sow_amt', string='Sow Debit')
    posted_sow_amt_credit = fields.Monetary(compute='_compute_posted_sow_amt', string='Sow Credit')

    # Calculate quantity for posted progress
    @api.multi
    def _compute_posted_progress_qty(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('progress_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_qty_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'qty_amount',
                                                                                 'progress_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_qty_amounts])
        data_debit_progress_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_progress_qty = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_qty_amount in account_project_qty_amounts:
            if account_project_qty_amount['qty_amount'] < 0.0:
                data_debit_progress_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']
            else:
                data_credit_progress_qty[account_project_qty_amount['account_project_id'][0]] += account_project_qty_amount[
                    'qty_amount']

        for account in self:
            account.posted_progress_qty_debit = abs(data_debit_progress_qty.get(account.id, 0.0))
            account.posted_progress_qty_credit = data_credit_progress_qty.get(account.id, 0.0)
            account.posted_progress_qty_balance = account.posted_progress_qty_credit - account.posted_progress_qty_debit

    posted_progress_qty_balance = fields.Float(compute='_compute_posted_progress_qty', string='Progress Qty')
    posted_progress_qty_debit = fields.Float(compute='_compute_posted_progress_qty', string='Progress Qty Debit')
    posted_progress_qty_credit = fields.Float(compute='_compute_posted_progress_qty', string='Progress Qty Credit')

    # Calculate man hours for posted progress
    @api.multi
    def _compute_posted_progress_mhr(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('progress_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'mhr_amount',
                                                                                 'progress_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_mhr_amounts])
        data_debit_progress_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_progress_mhr = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_mhr_amount in account_project_mhr_amounts:
            if account_project_mhr_amount['mhr_amount'] < 0.0:
                data_debit_progress_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_progress_mhr[account_project_mhr_amount['account_project_id'][0]] += account_project_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.posted_progress_mhr_debit = abs(data_debit_progress_mhr.get(account.id, 0.0))
            account.posted_progress_mhr_credit = data_credit_progress_mhr.get(account.id, 0.0)
            account.posted_progress_mhr_balance = account.posted_progress_mhr_credit - account.posted_progress_mhr_debit

    posted_progress_mhr_balance = fields.Float(compute='_compute_posted_progress_mhr', string='Progress mhr')
    posted_progress_mhr_debit = fields.Float(compute='_compute_posted_progress_mhr', string='Progress mhr Debit')
    posted_progress_mhr_credit = fields.Float(compute='_compute_posted_progress_mhr', string='Progress mhr Credit')

    # Calculate amounts for posted progress
    @api.multi
    def _compute_posted_progress_amt(self):
        analytic_wbs_line_obj = self.env['account.analytic_wbs.progress_line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('progress_transaction_state', '=', 'posted')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'amount',
                                                                                 'progress_transaction_state'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit_progress_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit_progress_amt = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['amount'] < 0.0:
                data_debit_progress_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']
            else:
                data_credit_progress_amt[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'amount']

        for account in self:
            account.posted_progress_amt_debit = abs(data_debit_progress_amt.get(account.id, 0.0))
            account.posted_progress_amt_credit = data_credit_progress_amt.get(account.id, 0.0)
            account.posted_progress_amt_balance = account.posted_progress_amt_credit - account.posted_progress_amt_debit

    posted_progress_amt_balance = fields.Monetary(compute='_compute_posted_progress_amt', string='Progress')
    posted_progress_amt_debit = fields.Monetary(compute='_compute_posted_progress_amt', string='Progress Debit')
    posted_progress_amt_credit = fields.Monetary(compute='_compute_posted_progress_amt', string='Progress Credit')

    # Calculate committed amounts
    @api.multi
    def _compute_po_amt(self):
        analytic_wbs_line_obj = self.env['purchase.order.line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('state', '=', 'purchase')]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'price_subtotal'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['price_subtotal'] < 0.0:
                data_debit[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'price_subtotal']
            else:
                data_credit[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'price_subtotal']

        for account in self:
            account.po_debit = abs(data_debit.get(account.id, 0.0))
            account.po_credit = data_credit.get(account.id, 0.0)
            account.po_balance = account.po_credit - account.po_debit

    po_balance = fields.Monetary(compute='_compute_po_amt', string='Committed PO')
    po_debit = fields.Monetary(compute='_compute_po_amt', string='Committed PO Debit')
    po_credit = fields.Monetary(compute='_compute_po_amt', string='Committed PO Credit')

    # Calculate invoiced amounts
    @api.multi
    def _compute_invoice_amt(self):
        analytic_wbs_line_obj = self.env['account.invoice.line']
        domain = [('account_project_id', 'in', self.mapped('id')), ('invoice_id.state', 'in', ['open', 'paid'])]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_project_amt_amounts = analytic_wbs_line_obj.search_read(domain, ['account_project_id', 'price_subtotal_signed'])
        account_project_ids = set([line['account_project_id'][0] for line in account_project_amt_amounts])
        data_debit = {account_project_id: 0.0 for account_project_id in account_project_ids}
        data_credit = {account_project_id: 0.0 for account_project_id in account_project_ids}

        for account_project_amt_amount in account_project_amt_amounts:
            if account_project_amt_amount['price_subtotal_signed'] < 0.0:
                data_debit[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'price_subtotal_signed']
            else:
                data_credit[account_project_amt_amount['account_project_id'][0]] += account_project_amt_amount[
                    'price_subtotal_signed']

        for account in self:
            account.invoice_debit = abs(data_debit.get(account.id, 0.0))
            account.invoice_credit = data_credit.get(account.id, 0.0)
            account.invoice_balance = account.invoice_credit - account.invoice_debit

    invoice_balance = fields.Monetary(compute='_compute_invoice_amt', string='Invoiced')
    invoice_debit = fields.Monetary(compute='_compute_invoice_amt', string='Invoice Debit')
    invoice_credit = fields.Monetary(compute='_compute_invoice_amt', string='Invoice Credit')

    # Calculate invoiced amounts
    @api.multi
    def _compute_budget_variance(self):
        for rec in self:
            rec.bdgt_var = rec.posted_bdgt_amt_balance - rec.eac

    bdgt_var = fields.Monetary(compute='_compute_budget_variance', string='Budget Variance')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = "{}".format(record.name)
            result.append((record.id, name))
        return result

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
            'limit': 80,
            'domain': [('account_project_id', '=', self.id)],
            'context': {
                'default_account_project_id': self.id
            },
        }
        return res


class ResConfigSettingsAnalyticWbs(models.TransientModel):
    _inherit = 'res.config.settings'

    model_analytic_wbs_default_product = fields.Boolean('Purchase Order Product Default')
    model_analytic_wbs_default_product_tci = fields.Boolean('TCI Product Default')
    model_tci_no_default_product_taxe = fields.Boolean('TCI No Default Taxes on Products')
    model_tci_no_product_taxe = fields.Boolean('TCI No Taxes on Products')

    def update_map_pos(self):
        mapped_act = self.env['sap.actuals_line_mapped'].search([('purchase_order_id', '!=', False)])
        act = {}
        for line in mapped_act:
            if not line.tci_id.po_id:
                val = {
                    'po_id': line.purchase_order_id.id
                }
                act[line.tci_id] = val
        for key, values in act.items():
            key.update(values)

    def update_wbs_analytics(self):
        '''
        pwbs_ids = self.env['tci.analytic.project'].search([('rep_uid', '=', False)])
        tci_id = set([line['tci_id'][0] for line in pwbs_ids])
        for rec in tci_id:
            rec.update_analytic_project_line_ids()
        '''

        task_ids = self.env['project.task'].search([('rep_uid', '=', False)])
        for rec in task_ids:
            rec.get_repuid()

        pwbs_ids = self.env['tci.analytic.project'].search([])
        tci_id = set([line['tci_id'][0] for line in pwbs_ids])
        for rec in tci_id:
            rec.update_analytic_project_line_ids()

    def generate_project_wbs(self):
        company_wbs = self.env['account.analytic_wbs.account'].search([('is_active', '=', True)])
        projects = self.env['project.project'].search([('active', '=', True)])
        for project in projects:
            wbs_account_ids = self.env['account.analytic_wbs.project'].search_read(
                [('project_id', '=', project.id)], ['account_id'])
            account_ids = set([line['account_id'][0] for line in wbs_account_ids])

            missing_account_wbs_ids = company_wbs.search([('is_old_wbs', '=', project.old_wbs), ('id', 'not in', list(account_ids))])

            new_project_wbs = []
            for wbs in missing_account_wbs_ids:
                if project.old_wbs:
                    name = project.project_code_id + "." + wbs.name
                else:
                    name = project.project_code_id + "-" + wbs.name
                line_val = {
                    'is_active': False,
                    'account_id': wbs.id,
                    'project_id': project.id,
                    'name': name,
                    'descr_short': wbs.descr_short,
                    'project_account_type': 'archived',
                }
                new_project_wbs.append(line_val)
                
            self.env['account.analytic_wbs.project'].create(new_project_wbs)

            #company_wbs = self.env['account.analytic_wbs.account'].search([('is_active', '=', True)])


        '''
        pwbs_ids = self.env['tci.analytic.project'].search([('rep_uid', '=', False)])
        tci_id = set([line['tci_id'][0] for line in pwbs_ids])
        for rec in tci_id:
            rec.update_analytic_project_line_ids()
        '''
        '''
        task_ids = self.env['project.task'].search([('rep_uid', '=', False)])
        for rec in task_ids:
            rec.get_repuid()

        pwbs_ids = self.env['tci.analytic.project'].search([])
        tci_id = set([line['tci_id'][0] for line in pwbs_ids])
        for rec in tci_id:
            rec.update_analytic_project_line_ids()
        '''