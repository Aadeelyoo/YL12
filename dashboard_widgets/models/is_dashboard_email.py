from odoo import api, fields, models


class DashboardEmail(models.Model):
    _name = 'is.dashboard.email'
    _description = "Dashboard Email"

    name = fields.Char(string="Subject")

    dashboard_ids = fields.Many2many(comodel_name="is.dashboard.widget", string="Dashboards")

    preview = fields.Html(compute="compute_preview")

    def action_send(self):
        for rec in self:
            pass

    @api.depends(
        'name',
        'dashboard_ids',
    )
    def compute_preview(self):
        for rec in self:
            rec.preview = self.env['ir.qweb'].render('dashboard_widgets.dashboard_email', values={'dashboard': rec})
