# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class res_partner_sap(models.Model):
    _inherit = 'res.partner'

    # set internal reference as sap vendor #
    @api.multi
    def create_new_vendor(self, code, name):
        # get the default ID (alberta in our case)
        fiscal_position = self.env.ref('l10n_ca.fiscal_position_template_ab_en').id
        new_vendor = {
            'name': name,
            'ref': code,
            'display_name': name,
            'lang': 'en_US',
            'active': True,
            'customer': False,
            'supplier': True,
            'employee': False,
            'type': 'contact',
            'is_company': True,
            'property_account_position_id': fiscal_position,
        }
        new_record = self.create(new_vendor)
        if not new_record:
            raise Warning('New record not created - tell your administrator to investigate why this is happening')
        return new_record

    @api.multi
    def get_partner_from_sap_code(self, code):
        partner_id = self.search([('ref', '=', code), ])
        if partner_id:
            return partner_id
        else:
            return False


