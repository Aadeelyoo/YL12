from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as safe_eval
from datetime import datetime, date


class DashboardWidgetNotes(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    note = fields.Text(string="Internal Notes")
    note_kanban = fields.Html(string="Notes On Dashboard")
