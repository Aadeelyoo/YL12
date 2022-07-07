# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class wbs_sow_line(models.Model):
    _name = 'wbs.sow_line'
    _description = 'wbs Sow Line'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Description', required=True)
    date = fields.Datetime('Date', required=True, index=True, default=fields.Datetime.now)
    amount = fields.Monetary('Amount', default=0.0)
    qty_amount = fields.Float('Quantity', default=0.0)
    mhr_amount = fields.Float('Man Hours', default=0.0)
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')
    line_id = fields.Many2one('wbs.sow', 'Sow Transaction', required=True, ondelete='cascade')
    sow_transaction_state = fields.Selection(related="line_id.state", string="Transaction State", readonly=True, store=True)


    #project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State", readonly=True, store=True)
    partner_id = fields.Many2one(related="line_id.partner_id", string='Partner', readonly=True)

    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    tag_ids = fields.Many2many('account.analytic_wbs.tag', 'wbs_sow_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)
    company_id = fields.Many2one('res.company', string = 'Company', required = True, default = lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    @api.onchange('account_project_id')
    def onchange_account_project(self):
        res = {}
        if self.line_id:
            ids = self.line_id.project_id.analytic_wbs_project_ids.mapped('id')
            res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res

    @api.multi
    def unlink(self):
        for order in self:
            if order.line_id.state != 'draft' and order.line_id.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" sow transactions can be modified '))
        return super(wbs_sow_line, self).unlink()


class wbs_sow(models.Model):
    _name = 'wbs.sow'
    _description = 'Sow Transaction'
    _inherit = ['mail.thread']
    _parent_name = 'parent_id'
    _parent_store = True
    _parent_order = 'name asc'
    _order = 'parent_right asc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    @api.model
    def _default_name(self):
        seq_id = self.env['ir.sequence'].get('sow.transaction.number')
        return self.env.context.get('name', seq_id)

    name = fields.Char('SOW', required=True, default=_default_name, track_visibility='onchange', translate=True)
    #date = fields.Datetime('Created', required=True, index=True, default=fields.Datetime.now)
    description = fields.Char('Description', required=False)
    body = fields.Text('Body', required=False)
    #project_id = fields.Many2one('project.project', string='Project', required=False, ondelete='restrict', track_visibility='onchange')
    transaction_type_id = fields.Many2one('wbs.sow_type', 'Transaction Type', required=False, ondelete='restrict')
    transaction_detail_ids = fields.One2many('wbs.sow_line', 'line_id', string='Transaction Detail')
    # todo Change selection fields value for something more related to the SOW status (with approval process) Include status included on PO
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
    ], default='draft', track_visibility='onchange')

    po_id = fields.Many2one(comodel_name='purchase.order', string='Purchasse Order', ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', track_visibility='onchange')

    user_id = fields.Many2one('res.users', string='Created By', default=_default_user, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    # Task related fields
    sow_type = fields.Selection([
        ('bdgtremain', 'Remaining Budget'),
        ('po', 'Purchasse Order'),
        ('act', 'Actual Item'),
        ('other', 'Other'),
    ], default='bdgtremain', track_visibility='onchange')

    task_ids = fields.One2many('project.task', 'sow_id', string='Tasks', ondelete='restrict')

    # SOW Hierarchy
    parent_id = fields.Many2one(comodel_name='wbs.sow', string='Parent SOW', ondelete='restrict', index=True)
    child_ids = fields.One2many(comodel_name='wbs.sow', inverse_name='parent_id', string='Child SOW')
    parent_path = fields.Char(index=True)
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)

    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise models.ValidationError(
                'Error! You cannot create recursive categories.')

    # todo onchange po_id from parent sow, change po_id of all sub sow as well as all tasks and sub_task

    # Count Fields
    child_count = fields.Integer(compute='compute_child_count', string='Child Count')
    task_count = fields.Integer(compute='compute_task_count', string='Task Count')

    is_active = fields.Boolean('Active', index=True, default=True)

    temp_target_amount = fields.Float(string='Temp Target', digits=dp.get_precision('Account'))


    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        for record in self:
            # alidate if partner_id is the owner of the PO, if not, change vendor
            po_id = record.po_id
            if po_id:
                if not po_id.partner_id.id == record.partner_id.id:
                    record.partner_id = po_id.partner_id.id
                    # todo: change domain of tasks to get only those related to the PO
            if not po_id:
                print('do nothing')

        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = {}
        for record in self:
            # validate if po_id and task_ids are relevant to this partner, if not, change it.
            partner = record.partner_id
            po = record.po_id

            if partner:
                partner_pos = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
                if po:
                    if not po.partner_id.id == partner.id:
                        record.po_id = False
                res['domain'] = {
                    'po_id': [('id', 'in', partner_pos.ids)],
                }

            if not partner:
                res['domain'] = {
                    'po_id': [],
                }
            # print(res)
        return res

    @api.multi
    def compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)
    @api.multi
    def compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)


    @api.multi
    def _sow_transaction_draft(self):
        self.write({'state' : 'draft' })
        return True

    @api.multi
    def _sow_transaction_submitted(self):
        self.write({ 'state' : 'submitted' })
        return True

    @api.multi
    def _sow_transaction_pending(self):
        self.write({'state': 'pending'})
        return True

    @api.multi
    def _sow_transaction_approved(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def _sow_transaction_posted(self):
        self.write({'state': 'posted'})
        return True

    @api.multi
    def _sow_transaction_rejected(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and order.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" sow transactions can be deleted '))
        return super(wbs_sow, self).unlink()

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage' in init_values:
            return 'project.mt_progrtrans_stage'
        return super(wbs_sow, self)._track_subtype(init_values)

    # Calculate Sow Transaction Man Hours
    @api.multi
    def _compute_transaction_mhr(self):
        analytic_wbs_line_obj = self.env['wbs.sow_line']
        domain = [('line_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        transaction_mhr_amounts = analytic_wbs_line_obj.search_read(domain, ['line_id', 'mhr_amount'])
        line_ids = set([line['line_id'][0] for line in transaction_mhr_amounts])
        data_debit_mhr = {line_id: 0.0 for line_id in line_ids}
        data_credit_mhr = {line_id: 0.0 for line_id in line_ids}

        for transaction_mhr_amount in transaction_mhr_amounts:
            if transaction_mhr_amount['mhr_amount'] < 0.0:
                data_debit_mhr[transaction_mhr_amount['line_id'][0]] += transaction_mhr_amount[
                    'mhr_amount']
            else:
                data_credit_mhr[transaction_mhr_amount['line_id'][0]] += transaction_mhr_amount[
                    'mhr_amount']

        for account in self:
            account.transaction_mhr_debit = abs(data_debit_mhr.get(account.id, 0.0))
            account.transaction_mhr_credit = data_credit_mhr.get(account.id, 0.0)
            account.transaction_mhr_balance = account.transaction_mhr_credit - account.transaction_mhr_debit

    transaction_mhr_balance = fields.Float(compute='_compute_transaction_mhr', string='Mhr')
    transaction_mhr_debit = fields.Float(compute='_compute_transaction_mhr', string='Mhr Debit')
    transaction_mhr_credit = fields.Float(compute='_compute_transaction_mhr', string='Mhr Credit')

    # Calculate Sow Transaction Amount
    @api.multi
    def _compute_transaction_amt(self):
        analytic_wbs_line_obj = self.env['wbs.sow_line']
        domain = [('line_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        transaction_amounts = analytic_wbs_line_obj.search_read(domain, ['line_id', 'amount'])
        line_ids = set([line['line_id'][0] for line in transaction_amounts])
        data_debit_amt = {line_id: 0.0 for line_id in line_ids}
        data_credit_amt = {line_id: 0.0 for line_id in line_ids}

        for transaction_amount in transaction_amounts:
            if transaction_amount['amount'] < 0.0:
                data_debit_amt[transaction_amount['line_id'][0]] += transaction_amount[
                    'amount']
            else:
                data_credit_amt[transaction_amount['line_id'][0]] += transaction_amount[
                    'amount']

        for account in self:
            account.transaction_amt_debit = abs(data_debit_amt.get(account.id, 0.0))
            account.transaction_amt_credit = data_credit_amt.get(account.id, 0.0)
            account.transaction_amt_balance = account.transaction_amt_credit - account.transaction_amt_debit

    transaction_amt_balance = fields.Monetary(compute='_compute_transaction_amt', string='Amount')
    transaction_amt_debit = fields.Monetary(compute='_compute_transaction_amt', string='Amount Debit')
    transaction_amt_credit = fields.Monetary(compute='_compute_transaction_amt', string='Amount Credit')

    # Button functions management
    @api.multi
    def display_child(self):
        self.ensure_one()
        res = {
            'name': 'Sub SOW',
            'type': 'ir.actions.act_window',
            'res_model': 'wbs.sow',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 80,
            'domain': [('id', 'child_of', self.id)],
            'context': {
                'parent_id': self.id,
                'default_parent_id': self.id
            },
        }
        return res

    @api.multi
    def display_task(self):
        self.ensure_one()
        res = {
            'name': 'Task',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 80,
            'domain': [('sow_id', '=', self.id)],
            'context': {
                'sow_id': self.id,
                'default_sow_id': self.id
            },
        }
        return res

class wbs_sow_type(models.Model):
    _name = 'wbs.sow_type'
    _description = 'Sow Transaction Status'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    description = fields.Char('Description', required=True)
    order = fields.Integer('Order', default=99)
    is_active = fields.Boolean('Active', default=False)

    user_id = fields.Many2one('res.users', string='User', default=_default_user)