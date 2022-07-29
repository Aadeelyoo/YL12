# Copyright 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ingeritprodsale(models.Model):
    _inherit = 'product.supplierinfo'

    vendor_code = fields.Char(string="Vendor Code")
    lead_time = fields.Char(string="lead_time")
    description = fields.Char(string = "Description")

