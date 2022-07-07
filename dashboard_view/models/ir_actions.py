# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _

class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'
    
    view_mode = fields.Selection(selection_add=[('dashboard', 'Dashboard')])
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: