# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import osv

import odoo.addons.decimal_precision as dp


class TciTemplateWbsSplitLine(models.Model):
    _name = "tci.template.wbs_split_line"
    _description = "TCI Split by WBS"
    _order = 'id'

    tci_template_id = fields.Many2one('tci.template', string='TCI Template', ondelete='cascade', index=True)
    name = fields.Char(string='WBS Description', required=False)
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS')
    percent_split = fields.Float(string='% Allocation')
    amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency', related='tci_template_id.po_id.currency_id', store=True,
                                  readonly=True)


class TciTemplateLine(models.Model):
    _name = 'tci.template.line'
    _description = 'Tci Template Line'
    _order = 'sequence asc, id'
    _rec_name = 'description'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    sequence = fields.Integer(string='Sequence', default='1')

    tci_template_id = fields.Many2one('tci.template', string='TCI Template', required=True, ondelete='cascade')
    wbs_state = fields.Selection(related="analytic_project_id.account_id.account_type",
                                 string="wbs State", readonly=True, store=True)
    project_wbs_state = fields.Selection(related="analytic_project_id.project_account_type",
                                         string="Project wbs State", readonly=True, store=True)
    po_id = fields.Many2one(related="tci_template_id.po_id", string='Purchase Order', readonly=True)

    product_id = fields.Many2one('product.product', string='Product', domain=[], required=False)
    name = fields.Char(string='Product Description', readonly=False, required=False)
    description = fields.Char('Line Description', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, readonly=False,
                             default=lambda self: self.env['uom.uom'].search([], limit=1, order='id'))
    unit_amount = fields.Float(string='Unit Price', readonly=False, required=True,
                               digits=dp.get_precision('Product Price'))
    quantity = fields.Float(required=True, readonly=False, digits=dp.get_precision('Product Unit of Measure'),
                            default=1)
    tci_line_tax_ids = fields.Many2many('account.tax', 'tci_template_tax', 'tci_template_id', 'tax_id', string='Taxes',
                                        readonly=False)
    untaxed_amount = fields.Float(string='Amount', store=True, compute='_compute_amount',
                                  digits=dp.get_precision('Account'))
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_project_id = fields.Many2one('account.analytic_wbs.project', string='Project WBS')
    account_id = fields.Many2one('account.account', string='Account',
                                 default=lambda self: self.env['ir.property'].get('property_account_expense_categ_id',
                                                                                  'product.category'))
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    @api.model
    def _compute_amount(self):
        for rec in self():
            rec.untaxed_amount = rec.quantity * rec.unit_amount

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
                'analytic_project_id': [('id', 'in', project_wbs_ids)],
                }
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = {}
        for record in self:
            # get product_id.name and modify template name field
            order_line_ids = self.env['purchase.order.line'].search([('order_id', '=', record.po_id.id)])
            project_wbs_ids = []
            for line in order_line_ids:
                wbs = line.account_project_id
                if wbs.id not in project_wbs_ids:
                    project_wbs_ids.append(wbs.id)
            res['domain'] = {
                'analytic_project_id': [('id', 'in', project_wbs_ids)],
                }
        return res


class TciTemplate(models.Model):
    _name = 'tci.template'
    _description = 'TCI Template'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Description', readonly=False, required=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.uid)
    tci_template_line_ids = fields.One2many('tci.template.line', 'tci_template_id', string='TCI Template Lines')
    po_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, track_visibility='onchange')

    active = fields.Boolean('Active', index=True, default=True)
    default_template = fields.Boolean('Use as Default Template', index=True, default=False)

    # TCI Account assignation template fields
    account_ass_method = fields.Selection([
        ('line', 'By Line'),
        ('tci', 'By TCI')
    ], string='Account Assignation', default='line', copy=True,
        help="Cost assignation behaviour. By line item or by tci")
    by_tci_calc_method = fields.Selection([
        ('percent', 'By Percent'),
        ('amount', 'By Amount')
    ], string='Calculation Method', default='percent', copy=True,
        help="Calculation method when using Account Assignation By TCI")
    tci_split_line_ids = fields.One2many('tci.template.wbs_split_line', 'tci_template_id', string='Tci Split Lines',
                                         copy=True)
    vendor_id = fields.Many2one(related='po_id.partner_id', string='Vendor', store=True)

    templ_approvers_ids = fields.One2many(
        'tci.template.approvers',
        'tci_template_id',
        string='Tci Template Approvers',
    )

    @api.multi
    def duplicate_template(self):
        """
        This is to duplicate template
        """
        self.copy(default={
            'name': self.name,
            'po_id': self.po_id.id,
            'active' : self.active,
            'default_template' : self.default_template,
            'account_ass_method' : self.account_ass_method,
            'by_tci_calc_method' : self.by_tci_calc_method,
            'tci_template_line_ids': self.tci_template_line_ids,
        })
        return True

    # Modify copy method to duplicate O2M fields inside object
    @api.multi
    def copy(self, default=None):
        res =  super(TciTemplate, self).copy(default)
        if self.tci_template_line_ids:
            for line in self.tci_template_line_ids:
                line.copy(default={
                    'tci_template_id': res.id,
                    })
        if self.tci_split_line_ids:
            for line in self.tci_split_line_ids:
                line.copy(default={
                    'tci_template_id': res.id,
                    })
        return res



class TciTemplatePurcheseOrder(models.Model):

    _inherit = "purchase.order"
    tci_template_ids = fields.One2many('tci.template', 'po_id', string='TCI Templates')


#TCI TEMPLATE APPROVERS
class TciTemplateApprovers(models.Model):
    _name = 'tci.template.approvers'
    _description = 'TCI Template Approvers'

    # Fields Declaration
    user_id = fields.Many2one('res.users', string='Related User', ondelete='cascade', index=True)
    activity_type = fields.Many2one('mail.activity.type', string='Activity Type', ondelete='restrict',
                                    domain=[('category', '=', 'approval')])
    tci_template_id = fields.Many2one('tci.template',string='Tci Template',)