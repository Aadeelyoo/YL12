from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"

    activate_adobe_sign = fields.Boolean("Activate Adobe Sign")
    adobe_sign_account_id = fields.Many2one("adobe.credentials", string="Adobe Account")