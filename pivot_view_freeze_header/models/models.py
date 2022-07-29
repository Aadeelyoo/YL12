from odoo import models, fields, api


class PivotViesState(models.TransientModel):
   
    _inherit = 'res.config.settings'
    pivot_view_state_head = fields.Boolean(config_parameter='base_setup.pivot_view_state')


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    
    def session_info(self):
        rec = super(Http, self).session_info()
        rec['pivot_view_state_head'] = self.env['ir.config_parameter'].sudo().get_param('base_setup'
                                                                                         '.pivot_view_state')
        return rec
