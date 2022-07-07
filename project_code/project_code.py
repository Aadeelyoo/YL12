# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of project_code, an Odoo module.
#
#     Copyright (c) 2016 Yannick Lessard
#
#     project_code is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     project_code is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with project_code.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import fields, models, api
from odoo.osv import expression


class project_code(models.Model):

    _inherit = 'project.project'

    project_code_id = fields.Char(string='Project Code', size=10, default=lambda self: self.env['ir.sequence'].next_by_code('project.sub.number'))
    short_name = fields.Char(string='Short Name')
    phase = fields.Char(string='Phase')

    @api.multi
    def name_get(self):
        result = []
        for project in self:
            if project.short_name:
                result.append((project.id, "%s" % (project.short_name,)))
            else:
                result.append((project.id, "%s" % (project.name,)))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('project_code_id', operator, name), ('short_name', operator, name)]
        purchase_order_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return self.browse(purchase_order_ids).name_get()