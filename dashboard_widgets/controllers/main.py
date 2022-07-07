import odoo.http as http
from odoo.http import request


class DashboadWidgetsHelper(http.Controller):

    @http.route('/dashboard/html/<int:widget_id>', type='http', auth='user', website=True)
    def dashboard_widget_html(self, widget_id, **kwargs):
        widget = request.env['is.dashboard.widget'].browse(widget_id).exists()
        if not widget:
            widget = request.env['is.dashboard.widget.preview'].browse(widget_id).exists()
        if widget and widget.html:
            return widget.html
        else:
            return 'Please save record first to preview'
