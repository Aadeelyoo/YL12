from odoo import api, fields, models


class IsDashbaordWidgetGraph(models.AbstractModel):
    _name = 'is.dashboard.widget.abstract'

    display_mode = fields.Selection(selection_add=[
        ('graph', 'Chart / Graph'),
    ])
