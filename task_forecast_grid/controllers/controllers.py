# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import werkzeug


class TaskForecastController(http.Controller):

    @http.route(['/forecast'], type='http', auth="user", website=True, sitemap=False)
    def forecast_list(self, profile_id=False, **kw):
        server_action = http.request.env.ref("task_forecast_grid.get_specific_task")

        url = str("web?&#action={}".format(server_action.id))

        internalref = kw.get('internalref')
        if internalref:
            url += str("&internalref={}".format(internalref))

        po_id = kw.get('po_id')
        if po_id:
            url += str("&po_id={}".format(po_id))

        project_wbs = kw.get('project_wbs')
        if project_wbs:
            url += str("&project_wbs={}".format(project_wbs))

        project_wbs_id = kw.get('project_wbs_id')
        if project_wbs_id:
            url += str("&project_wbs_id={}".format(project_wbs_id))

        employee_id = kw.get('employee_id')
        if employee_id:
            url += str("&employee_id={}".format(employee_id))

        project_code = kw.get('project_code')
        if project_code:
            url += str("&project_code={}".format(project_code))

        task_id = kw.get('task_id')
        if task_id:
            url += str("&task_id={}".format(task_id))

        partner_id = kw.get('partner_id')
        if partner_id:
            url += str("&partner_id={}".format(partner_id))

        month = kw.get('month')
        if month:
            url += str("&month={}".format(month))

        return werkzeug.utils.redirect(url)


