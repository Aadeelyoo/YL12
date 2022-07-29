from . import models
from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    for rec in env['ir.config_parameter'].search([]):
        if rec.key == "base_setup.pivot_view_state":
            rec.sudo().unlink()
