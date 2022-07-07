# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class purchase_workticket_line(models.Model):
    _name = 'purchase.workticket.line'
    _description = 'Workticket Line'
    _order = 'date desc, id desc'
    _rec_name = 'description'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    description = fields.Char('Description', required=True)
    date = fields.Datetime('Date', required=True, index=True, default=fields.Datetime.now)
    qty = fields.Float('Quantity', default=1.0)
    uom = fields.Many2one('uom.uom', string='UOM', required=True)
    unit_rate = fields.Monetary('Unit Rate', default=0.0)

    untaxed_amount = fields.Float(string='Amount', store=True,
        compute='_compute_amount', digits=dp.get_precision('Account'))

    mhr = fields.Float('Labour Hours', default=0.0)
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')
    workticket_id = fields.Many2one('purchase.workticket', 'Workticket no', required=True, ondelete='cascade')
    state = fields.Selection(related="workticket_id.state", string="Transaction State", readonly=True, store=True)

    project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State", readonly=True, store=True)
    partner_id = fields.Many2one(related="workticket_id.partner_id", string='Vendor', readonly=True)
    po_id = fields.Many2one(related="workticket_id.po_id", string='Purchase Order', readonly=True)

    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    invoice_id = fields.Many2one(string="Invoice", readonly=True, related='workticket_id.invoice_id', store=True, copy=False)


    @api.depends('qty', 'unit_rate', 'currency_id')
    def _compute_amount(self):
        for record in self:
            record.untaxed_amount = record.unit_rate * record.qty
    '''
    @api.onchange('account_project_id')
    def onchange_account_project(self):
        res = {}
        if self.workticket_id:
            ids = self.workticket_id.project_id.analytic_wbs_project_ids.mapped('id')
            res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res
    '''

    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        for record in self:
            # get purchase.order.line account_project_ids
            order_line_ids = self.env['purchase.order.line'].search([('order_id', '=', record.po_id.id)])
            project_wbs_ids = []
            for line in order_line_ids:
                wbs = line.account_project_id
                if wbs.id not in project_wbs_ids:
                    project_wbs_ids.append(wbs.id)
            res['domain'] = {
                'account_project_id': [('id', 'in', project_wbs_ids)],
                }
            # print(res)
        return res

    @api.multi
    def unlink(self):
        for order in self:
            if order.workticket_id.state != 'draft' and order.workticket_id.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" LEMs can be modified '))
        return super(purchase_workticket_line, self).unlink()


class purchase_workticket(models.Model):
    _name = 'purchase.workticket'
    _description = 'PO LEMs'
    _inherit = ['mail.thread',]
    _order = 'date desc, id desc'
    _rec_name = 'partner_wtnumber'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('name')
    wtnumber = fields.Char('Internal #', readonly=True)
    partner_wtnumber = fields.Char('Vendor Ticket #', required=True)
    # todo insert here sql constraint to have unique wt number per partner per project

    date = fields.Date('Ticket Date', required=True, index=True, default=fields.Date.today)
    description = fields.Char('Description', required=False)
    workticket_type_id = fields.Many2one('purchase.workticket.type', 'Work Ticket Type', required=False, ondelete='restrict')
    workticket_line_ids = fields.One2many('purchase.workticket.line', 'workticket_id', string='Work Ticket Lines', readonly=True,
        states={'draft': [('readonly', False)], 'pending': [('readonly', False)], 'submitted': [('readonly', False)], 'rejected': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
    ], default='draft', track_visibility='onchange')

    user_id = fields.Many2one('res.users', string='Assigned To', default=_default_user, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    untaxed_amount = fields.Float(string='Untaxed Amount', store=True,
        compute='_compute_amount', digits=dp.get_precision('Account'), track_visibility='onchange')
    total_tax_amount = fields.Float(string='Tax Amount', store=True,
        compute='_compute_amount', digits=dp.get_precision('Account'))
    total_amount = fields.Float(string='Total Amount', store=True,
        compute='_compute_amount', digits=dp.get_precision('Account'))
    currency_id = fields.Many2one(related="company_id.currency_id",
        string="Currency", readonly=True)

    po_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, track_visibility='onchange')
    project_id = fields.Many2one(related="po_id.project_id", string='Project', ondelete='restrict', store=True)

    project_ids = fields.Many2many(relation='workticket_project_rel', comodel_name='project.project',
        column1='workticket_id', column2='project_id', readonly=True, compute='compute_project_ids')

    partner_id = fields.Many2one(related="po_id.partner_id", string='Vendor', ondelete='restrict', store=True)

    active = fields.Boolean('Active', index=True, default=True)

    attachment_ids = fields.One2many(comodel_name="ir.attachment",
        inverse_name="res_id", compute="_compute_attachment",
        string="Attachment Files")
    attachment_number = fields.Integer(compute='_compute_attachment', string='Number of Attachments')
    workticket_line_number = fields.Integer(compute='_compute_lines', string='Number of Lines')
    wttemplate_id = fields.Many2one('purchase.wttemplate', string='Work Ticket Template', readonly=True,
        states={'draft': [('readonly', False)], 'pending': [('readonly', False)], 'rejected': [('readonly', False)]})

    invoice_id = fields.Many2one('account.invoice', string="Invoice",readonly=False, copy=False)


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = {}
        #Validate if po_id belongs to partner_id
        if self.partner_id:
            po_ids = self.env['purchase.order'].search([('partner_id', '=', self.partner_id.id)])
            if self.po_id not in po_ids:
                print('supprimer le po_id')
                self.po_id = False
            res['domain'] = {'po_id': [('id', 'in', po_ids.ids)]}
        return res

    @api.onchange('po_id')
    def onchange_po_id(self):
        res = {}
        if self.po_id:
            # get workticket templates related to the PO
            wttemplate_ids = self.env['purchase.wttemplate'].search([('po_id', '=', self.po_id.id)])
            if self.wttemplate_id not in wttemplate_ids:
                self.wttemplate_id = False

            res['domain'] = {
                'wttemplate_id': [('id', 'in', wttemplate_ids.ids)]
                }

        return res


    '''
    @api.onchange('po_id')
    def onchange_po_id2(self):
        res = {}
        if self.po_id:
            ids = self.po_id.order_line.account_project_id.mapped('id')
            print(ids)
            res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res
    '''

    @api.onchange('wttemplate_id')
    def import_template_lines(self):
        if self.wttemplate_id:
            wttemplate_lines = self._get_wttemplate_line()
            wt_lines = self.workticket_line_ids
            for line in wttemplate_lines:
                wt_lines += wt_lines.new(line)
            self.workticket_line_ids = wt_lines

    @api.multi
    def _get_wttemplate_line(self):
        wttemplate_line = []
        company = self.po_id.company_id
        for line in self.wttemplate_id.wttemplate_line_ids:
            new_lines = {
                'description': line.description,
                'qty': line.qty,
                'uom': line.uom,
                'unit_rate': line.unit_rate,
                'account_project_id': line.account_project_id,
                'workticket_id': self._origin.id,
                'company_id': company,
            }
            wttemplate_line.append(new_lines)
        return wttemplate_line

    @api.one
    @api.depends('workticket_line_ids')
    def compute_project_ids(self):
        project_grouped = []
        for record in self.mapped('workticket_line_ids'):
            if record.project_id.id not in project_grouped:
                project_grouped.append(record.project_id.id)
        if project_grouped:
            self.project_ids = project_grouped

    @api.onchange('workticket_line_ids.untaxed_amount')
    def compute_amount(self):
        return self._compute_amount

    @api.one
    @api.depends('workticket_line_ids.untaxed_amount', 'currency_id', 'company_id', 'date')
    def _compute_amount(self):
        self.untaxed_amount = sum(line.untaxed_amount for line in self.workticket_line_ids)
        self.total_tax_amount = 0
        self.total_amount = self.untaxed_amount + self.total_tax_amount

    @api.multi
    def _compute_lines(self):
        for record in self:
            record.workticket_line_number = len(record.workticket_line_ids)

    @api.multi
    def _compute_attachment(self):
        for record in self:
            record.attachment_ids = self.env['ir.attachment'].search(
                [('res_model', '=', 'purchase.workticket'), ('res_id', '=', record.id)]).ids
            record.attachment_number = len(record.attachment_ids)

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'purchase.workticket'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'purchase.workticket', 'default_res_id': self.id}
        return res

    @api.multi
    def action_workticket_draft(self):
        print("button submit")
        self.write({'state': 'draft' })
        return True

    @api.multi
    def action_workticket_submit(self):
        self.write({'state': 'submitted' })
        return True

    @api.multi
    def action_workticket_pending(self):
        self.write({'state': 'pending'})
        return True

    @api.multi
    def action_workticket_approve(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def action_workticket_post(self):
        self.write({'state': 'posted'})
        return True

    @api.multi
    def action_workticket_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and order.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" LEMs can be deleted '))
        return super(purchase_workticket, self).unlink()

    # Calculate Worktickets Labour Hours from workticket lines

    workticket_mhr = fields.Float('Labour Hours', default=0.0)
    labour_amount = fields.Monetary('Labour', default=0.0)
    travel_amount = fields.Monetary('Travel', default=0.0)
    equipment_amount = fields.Monetary('Equipment', default=0.0)
    markup_amount = fields.Monetary('Markup', default=0.0)
    material_amount = fields.Monetary('Material', default=0.0)
    expense_amount = fields.Monetary('Expense', default=0.0)
    subcontract_amount = fields.Monetary('Sub-Contract', default=0.0)

    @api.model
    def create(self, vals):
        vals['wtnumber'] = self.env['ir.sequence'].next_by_code('purchase.workticket.number')
        return super(purchase_workticket, self).create(vals)


    @api.multi
    def button_generate_wh_doc(self):
        context = self._context
        partner = self.env['res.partner']
        res = {}
        for inv in self:
            view_id = self.env['ir.ui.view'].search([
                ('name', '=', 'account.invoice.wh.iva.customer')])
            context = self.env.context.copy()
            context.update({
                'domain':[
                    ('invoice_id','=',inv.id),
                    ('type','=',inv.type),
                    ('default_partner_id','=', partner._find_accounting_partner(inv.partner_id).id),
                    ('default_name' ,'=', inv.name or inv.number),
                    ('view_id' ,'=', view_id[0].id)
                ]
            })
        return {
            'name': _('Withholding vat customer'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.wh.iva',
            'view_type': 'form',
            'view_id': False,
            'view_mode': 'form',
            'target': 'current',
            'domain': [('type', '=', inv.type )],
            'context': context,
        }

class purchase_workticket_type(models.Model):
    _name = 'purchase.workticket.type'
    _description = 'Work Ticket Type'
    _order = 'name asc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    description = fields.Char('Description', required=True)
    order = fields.Integer('Order', default=99)
    is_active = fields.Boolean('Active', default=False)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)