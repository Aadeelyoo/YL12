from odoo import api, fields, models


class IsDashbaordWidgetStar(models.AbstractModel):
    _name = 'is.dashboard.widget.abstract'

    display_mode = fields.Selection(selection_add=[
        ('star', 'Star Rating'),
    ])
