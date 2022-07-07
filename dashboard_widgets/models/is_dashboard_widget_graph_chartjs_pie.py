from odoo import api, fields, models

from collections import OrderedDict


class DashboardWidgetGraph(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    def get_dashboard_data(self):
        if self.display_mode != 'graph' or self.graph_type != 'pie':
            return super(DashboardWidgetGraph, self).get_dashboard_data()

        data1, color1, area1, title1 = self.chart_get_data_query_1()
        # TODO: Allow data2 set to work
        # data2, color2, area2, title2 = self.chart_get_data_query_2()

        if not data1:
            return False

        data = {
            'type': 'pie',
            'show_values_on_graph': self.show_values_on_graph,
            'data': data1,
            'options': {},
        }

        if len(data['data']['datasets']) == 1:
            data['options']['legend'] = {
               'display': False,
            }
        return data
