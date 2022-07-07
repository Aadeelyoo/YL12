# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import pycompat

class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('dashboard', 'Dashboard')], string='View Type')
    
    @api.model
    def ref_to_view_id(self, xml_id):
        """ Return the view ID corresponding to ``xml_id``, which may be a
        view ID or an XML ID.
        """
        if not xml_id:
            return False
        
        if isinstance(xml_id, pycompat.integer_types):
            return xml_id
        
        if '.' not in xml_id:
            raise ValueError('Invalid ref id: %r' % xml_id)
        return self.env.ref(xml_id).id
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: