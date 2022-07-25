# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import Warning
from datetime import date, datetime


class purchase_order_sap(models.Model):
    _inherit = 'purchase.order'

    sap_actuals_mapped_ids = fields.One2many('sap.actuals_line_mapped', 'purchase_order_id', string='Actual Lines')
    actual_count = fields.Integer("Actuals Count", compute='_compute_actual_count')
    sap_open_po_mapped_ids = fields.One2many('sap.po_line_mapped', 'purchase_order_id', string='Open PO Lines')
    open_po_count = fields.Integer("Open PO Count", compute='_compute_open_po_count')
    is_new_import = fields.Boolean("Is New Import", default=False)

    # set internal reference as sap vendor #
    @api.multi
    def create_new_po(self, code, vendor, date_order):
        new_po = {
            'internal_ref': code,
            'partner_id': vendor.id,
            'state': 'purchase',
            'date_order': date_order,
            'is_new_import': True,
        }
        new_record = self.create(new_po)
        if not new_record:
            raise Warning('New record not created - tell your administrator to investigate why this is happening')
        return new_record

    @api.multi
    def get_po_from_sap_code(self, code):
        po_id = self.search([('internal_ref', '=', code), ])
        if po_id:
            return po_id
        else:
            return False

    # Computed SAP Money Values Fields
    @api.multi
    def _compute_sap_amt(self):
        sap_actuals_obj = self.env['sap.actuals_line_mapped']
        domain = [('purchase_order_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        sap_amounts = sap_actuals_obj.search_read(domain, ['purchase_order_id', 'val_ca_area_crcy'])
        purchase_order_ids = set([line['purchase_order_id'][0] for line in sap_amounts])
        data_debit_amt = {purchase_order_id: 0.0 for purchase_order_id in purchase_order_ids}
        data_credit_amt = {purchase_order_id: 0.0 for purchase_order_id in purchase_order_ids}

        for sap_amt in sap_amounts:
            if sap_amt['val_ca_area_crcy'] < 0.0:
                data_debit_amt[sap_amt['purchase_order_id'][0]] += sap_amt['val_ca_area_crcy']
            else:
                data_credit_amt[sap_amt['purchase_order_id'][0]] += sap_amt['val_ca_area_crcy']

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
            'domain': [('purchase_order_id', '=', self.id)],
            'context': {
                'purchase_order_id': self.id,
                'default_purchase_order_id': self.id,
            },
        }
        return res

    @api.multi
    def _compute_open_po_count(self):
        for rec in self:
            rec.open_po_count = len(rec.sap_open_po_mapped_ids)

    @api.multi
    def action_display_open_po(self):
        self.ensure_one()
        res = {
            'name': 'SAP Open PO',
            'type': 'ir.actions.act_window',
            'res_model': 'sap.open_po_line_mapped',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': False,
            'limit': 80,
            'domain': [('purchase_order_id', '=', self.id)],
            'context': {
                'purchase_order_id': self.id,
                'default_purchase_order_id': self.id,
            },
        }
        return res


class purchase_order_line_sap(models.Model):
    _inherit = 'purchase.order.line'

    sap_line_mapped = fields.Char(string='SAP Mapped Line')
    sap_create_date = fields.Date(string='SAP Created Date')

    @api.multi
    def create_new_po_line_from_sap(self, record):
        if record:
            product_id = self._get_product_default()
            product_uom = self.env.ref('uom.product_uom_unit')
            # map unit price and quantity based on the PO type from SAP (service lines or material lines)
            # All service lines on the data export have a created_on date. The material lines don't have this field
            # print(record)
            if record.created_on:
                unit_price = 1
                quantity = record.net_order_value
                if quantity:
                    qty_received = quantity - record.value_to_deliver
                else:
                    qty_received = 0
            if not record.created_on:
                unit_price = record.net_price
                quantity = record.order_quantity
                if quantity:
                    qty_received = quantity - record.qty_to_deliver
                else:
                    qty_received = 0

            new_po_line = {
                'date_planned': record.document_date,
                'name': record.short_text,
                'order_id': record.purchase_order_id.id,
                'price_unit': unit_price,
                'product_id': product_id,
                'product_qty': quantity,
                'product_uom': product_uom.id,
                'sap_line_mapped': record.computed_uid,
                'account_project_id': record.account_project_id.id,
                'sap_create_date': record.created_on,
                #'qty_invoiced': qty_invoiced,
                'qty_received': qty_received,
            }

            new_record = self.create(new_po_line)
            if not new_record:
                raise Warning('New po line record not created - tell your administrator to investigate why this is happening')
            return new_record