# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import osv
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


# todo: Modify class SOW transaction

# todo


class tci_wbs(models.Model):
    _name = 'tci.wbs'
    _description = 'TCI WBS'
    _order = 'sequence asc, id'

    def _compute_base_amount(self):
        wbs_grouped = {}
        for tci in self.mapped('tci_id'):
            wbs_grouped[tci.id] = tci.get_wbs_values()
        for wbs in self:
            wbs.base = 0.0
            if wbs.account_project_id:
                key = {
                    'account_project_id': wbs.account_project_id.id,
                }
                if wbs.tci_id and key in wbs_grouped[wbs.tci_id.id]:
                    wbs.base = wbs_grouped[wbs.tci_id.id][key]['base']
                else:
                    _logger.warning('wbs Base Amount not computable probably due to a change in an underlying wbs (%s).', wbs.account_project_id.name)

    tci_id = fields.Many2one('tci', 'Cost Item No', required=True, ondelete='cascade', index=True)
    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')


    qty = fields.Float('Quantity')
    uom = fields.Many2one('uom.uom', string='UOM', required=True)
    unit_rate = fields.Monetary('Unit Rate', default=0.0)

    untaxed_amount = fields.Float(string='Amount', store=True,
        compute='_compute_amount', digits=dp.get_precision('Account'))

    mhr = fields.Float('Labour Hours', default=0.0)

    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State", readonly=True, store=True)

    partner_id = fields.Many2one(related="tci_id.partner_id", string='Vendor', readonly=True)
    po_id = fields.Many2one(related="tci_id.po_id", string='Purchase Order', readonly=True)

    company_id = fields.Many2one('res.company', related='tci_id.company_id')

    #sheet_id = fields.Many2one(string="Expense Report", readonly=True, related='tci_id.sheet_id', store=True, copy=False)
    name = fields.Char(string='Tax Description', required=True)

    #account_id = fields.Many2one('account.account', string='Tax Account', required=True, domain=[('deprecated', '=', False)])
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of tci tax.")
    currency_id = fields.Many2one('res.currency', related='tci_id.currency_id', store=True, readonly=True)
    base = fields.Monetary(string='Base', compute='_compute_base_amount')

class tci_line(models.Model):
    _name = 'tci.line'
    _description = 'Task Cost Item Line'
    _order = 'sequence asc, id desc'
    _rec_name = 'description'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    date = fields.Datetime('Date', required=True, index=True, default=fields.Datetime.now)

    product_id = fields.Many2one('product.product', string='Product', readonly=False, required=False)
    description = fields.Char('Description', required=True)
    qty = fields.Float('Quantity', default=1.0)
    uom = fields.Many2one('uom.uom', string='UOM', required=True)
    unit_rate = fields.Monetary('Unit Rate', default=0.0)

    untaxed_amount = fields.Float(string='Amount', store=True, compute='_compute_amount',
                                  digits=dp.get_precision('Account'))

    mhr = fields.Float('Labour Hours', default=0.0)

    account_project_id = fields.Many2one('account.analytic_wbs.project', 'Project wbs', required=True, ondelete='restrict')
    uses_multiple_wbs = fields.Boolean('Multiple WBS')

    tci_id = fields.Many2one('tci', 'Cost Item No', required=True, ondelete='cascade')

    user_id = fields.Many2one('res.users', string='User', default=_default_user)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying the tci list.")

    invoice_id = fields.Many2one(string="Invoice", readonly=True, related='tci_id.invoice_id', store=True, copy=False)

    # related fields
    # project_id = fields.Many2one(related="account_project_id.project_id", string="Project", readonly=True, store=True)
    wbs_state = fields.Selection(related="account_project_id.account_id.account_type", string="wbs State",
                                 readonly=True, store=True)
    project_wbs_state = fields.Selection(related="account_project_id.project_account_type", string="Project wbs State",
                                         readonly=True, store=True)
    partner_id = fields.Many2one(related="tci_id.partner_id", string='Vendor', readonly=True)
    po_id = fields.Many2one(related="tci_id.po_id", string='Purchase Order', readonly=True)
    state = fields.Selection(related="tci_id.state", string="Transaction State", readonly=True, store=True)

    @api.depends('qty', 'unit_rate', 'currency_id')
    def _compute_amount(self):
        for record in self:
            record.untaxed_amount = record.unit_rate * record.qty
    '''
    def onchange_account_project(self):
        res = {}
        if self.tci_id:
            ids = self.tci_id.project_id.analytic_wbs_project_ids.mapped('id')
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
            if order.tci_id.state != 'draft' and order.tci_id.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" task cost items can be modified '))
        return super(tci_line, self).unlink()

class tci(models.Model):
    _name = 'tci'
    _description = 'Task Cost Item'
    _inherit = ['mail.thread', 'doc.approval']
    _order = 'date desc, id desc'
    _rec_name = 'partner_tci_number'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    # x name = fields.Char('name')
    # x tci_number = fields.Char('Internal #', readonly=True)

    # x partner_tci_number = fields.Char('Task Cost Item #', required=True)
    # todo insert here sql constraint to have unique wt number per partner per project

    # x date = fields.Date('TCI Date', required=True, index=True, default=fields.Date.today)
    # x description = fields.Char('Description', required=False)

    #task_id = fields.Many2one('project.task', 'Task', required=False, ondelete='restrict')

    # x tci_type_id = fields.Many2one('tci.type', 'TCI Type', required=False, ondelete='restrict')
    # x tci_line_ids = fields.One2many('tci.line', 'tci_id', string='TCI Lines', readonly=True,
    # x     states={'draft': [('readonly', False)], 'pending': [('readonly', False)], 'submitted': [('readonly', False)], 'rejected': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
    ], default='draft', track_visibility='onchange')

    # x user_id = fields.Many2one('res.users', string='Assigned To', default=_default_user, track_visibility='onchange')
    # x company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    #untaxed_amount = fields.Float(string='Untaxed Amount', store=True,
    #    compute='_compute_amount', digits=dp.get_precision('Account'), track_visibility='onchange')
    #total_tax_amount = fields.Float(string='Tax Amount', store=True,
    #    compute='_compute_amount', digits=dp.get_precision('Account'))
    #total_amount = fields.Float(string='Total Amount', store=True,
    #    compute='_compute_amount', digits=dp.get_precision('Account'))
    # x currency_id = fields.Many2one(related="company_id.currency_id",
    # x     string="Currency", readonly=True)

    # x po_id = fields.Many2one('purchase.order', string='Purchase Order', required=False, track_visibility='onchange')

    # x project_id = fields.Many2one(related="po_id.project_id", string='Project', ondelete='restrict', store=True)

    # x project_ids = fields.Many2many(relation='tci_project_rel', comodel_name='project.project',
    # x     column1='tci_id', column2='project_id', readonly=True, compute='compute_project_ids')

    partner_id = fields.Many2one(related="po_id.partner_id", string='Vendor', ondelete='restrict', store=True)

    active = fields.Boolean('Active', index=True, default=True)

    #attachment_ids = fields.One2many(comodel_name="ir.attachment",
    #    inverse_name="res_id", compute="_compute_attachment",
    #    string="Attachment Files")
    #attachment_number = fields.Integer(compute='_compute_attachment', string='Number of Attachments')
    tci_line_number = fields.Integer(compute='_compute_lines', string='Number of Lines')
    tci_template_id = fields.Many2one('tci.template', string='TCI Template', readonly=True,
        states={'draft': [('readonly', False)], 'pending': [('readonly', False)], 'rejected': [('readonly', False)]})

    invoice_id = fields.Many2one('account.invoice', string="Invoice",readonly=False, copy=False)


    '''
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
            # get TCI templates related to the PO
            tci_template_ids = self.env['tci.template'].search([('po_id', '=', self.po_id.id)])
            if self.tci_template_id not in tci_template_ids:
                self.tci_template_id = False

            res['domain'] = {
                'tci_template_id': [('id', 'in', tci_template_ids.ids)]
                }

        return res
    

    
    @api.onchange('po_id')
    def onchange_po_id2(self):
        res = {}
        if self.po_id:
            ids = self.po_id.order_line.account_project_id.mapped('id')
            print(ids)
            res['domain'] = {'account_project_id': [('id', 'in', ids)]}
        return res
    '''

    @api.onchange('tci_template_id')
    def import_template_lines(self):
        if self.tci_template_id:
            tci_template_lines = self._get_tci_template_line()
            tci_lines = self.tci_line_ids
            for line in tci_template_lines:
                tci_lines += tci_lines.new(line)
            self.tci_line_ids = tci_lines

    @api.multi
    def _get_tci_template_line(self):
        tci_template_line = []
        company = self.po_id.company_id
        for line in self.tci_template_id.tci_template_line_ids:
            new_lines = {
                'description': line.description,
                'qty': line.qty,
                'uom': line.uom,
                'unit_rate': line.unit_rate,
                'account_project_id': line.account_project_id,
                'tci_id': self._origin.id,
                'company_id': company,
            }
            tci_template_line.append(new_lines)
        return tci_template_line

    @api.one
    @api.depends('tci_line_ids')
    def compute_project_ids(self):
        project_grouped = []
        for record in self.mapped('tci_line_ids'):
            if record.project_id.id not in project_grouped:
                project_grouped.append(record.project_id.id)
        if project_grouped:
            self.project_ids = project_grouped

    @api.onchange('tci_line_ids.untaxed_amount')
    def compute_amount(self):
        return self._compute_amount





    @api.one
    @api.depends('tci_line_ids.untaxed_amount', 'currency_id', 'company_id', 'date')
    def _compute_amount(self):
        self.untaxed_amount = sum(line.untaxed_amount for line in self.tci_line_ids)
        self.total_tax_amount = 0
        self.total_amount = self.untaxed_amount + self.total_tax_amount

    @api.multi
    def _compute_lines(self):
        for record in self:
            record.tci_line_number = len(record.tci_line_ids)

    @api.multi
    def _compute_attachment(self):
        for record in self:
            record.attachment_ids = self.env['ir.attachment'].search(
                [('res_model', '=', 'tci'), ('res_id', '=', record.id)]).ids
            record.attachment_number = len(record.attachment_ids)

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'tci'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'tci', 'default_res_id': self.id}
        return res

    @api.multi
    def action_tci_draft(self):
        print("button submit")
        self.write({'state': 'draft' })
        return True

    @api.multi
    def action_tci_submit(self):
        self.write({'state': 'submitted' })
        return True

    @api.multi
    def action_tci_pending(self):
        self.write({'state': 'pending'})
        return True

    @api.multi
    def action_tci_approve(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def action_tci_post(self):
        self.write({'state': 'posted'})
        return True

    @api.multi
    def action_tci_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and order.state != 'pending':
                raise osv.except_osv(('Error'), ('Only "Draft" and "Pending" Task Cost Items can be deleted '))
        return super(tci, self).unlink()

    # Calculate Tcis Labour Hours from cost Item Lines

    tci_mhr = fields.Float('Labour Hours', default=0.0)
    labour_amount = fields.Monetary('Labour', default=0.0)
    travel_amount = fields.Monetary('Travel', default=0.0)
    equipment_amount = fields.Monetary('Equipment', default=0.0)
    markup_amount = fields.Monetary('Markup', default=0.0)
    material_amount = fields.Monetary('Material', default=0.0)
    expense_amount = fields.Monetary('Expense', default=0.0)
    subcontract_amount = fields.Monetary('Sub-Contract', default=0.0)

    @api.model
    def create(self, vals):
        vals['tci_number'] = self.env['ir.sequence'].next_by_code('tci.number')
        return super(tci, self).create(vals)


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
                    ('default_name','=', inv.name or inv.number),
                    ('view_id','=', view_id[0].id)
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
            'domain': [('type', '=', inv.type)],
            'context': context,
        }


class tci_type(models.Model):
    _name = 'tci.type'
    _description = 'Task Cost Item Type'
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


class task_tci(models.Model):
    _inherit = ['project.task']

    tci_ids = fields.One2many('tci', 'task_id', string='Cost Items')
    tci_number = fields.Integer(compute='_compute_tci', string='Number of TCI')
    sow_id = fields.Many2one('wbs.sow', string='SOW', required=False)


    @api.multi
    def _compute_tci(self):
        for record in self:
            record.tci_number = len(record.tci_ids)

    @api.multi
    def display_tci(self):
        self.ensure_one()
        res = {
            'name': 'TCI',
            'type': 'ir.actions.act_window',
            'res_model': 'tci',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'limit': 80,
            'domain': [('task_id', '=', self.id)],
            'context': {
                'task_id': self.id,
                'default_task_id': self.id
            },
        }
        return res