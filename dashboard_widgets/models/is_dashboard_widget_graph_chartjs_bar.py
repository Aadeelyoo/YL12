from odoo import api, fields, models

from collections import OrderedDict


class DashboardWidgetGraph(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    graph_1_bar_stacked = fields.Boolean("Stack Bar Chart (1)")

    def get_dashboard_data(self):
        if self.display_mode != 'graph' or self.graph_type != 'bar':
            return super(DashboardWidgetGraph, self).get_dashboard_data()

        data1, color1, area1, title1 = self.chart_get_data_query_1()
        # TODO: Allow data2 set to work
        # data2, color2, area2, title2 = self.chart_get_data_query_2()

        if not data1:
            return False

        data = {
            'type': 'bar',
            'show_values_on_graph': self.show_values_on_graph,
            'data': data1,
            'options': {},
        }

        if self.query_1_config_enable_goal and data1['dates']:
            ds = self.get_dataset_for_goal_1(data1['dates'], data1['labels'])

            if self.graph_1_bar_stacked:
                ds['stack'] = 'Stack 1'

            if self.chart_1_goal_config_color:
                ds['borderColor'] = self.chart_1_goal_config_color
                ds['backgroundColor'] = self.chart_1_goal_config_color

            data['data']['datasets'].append(ds)

        if self.graph_1_bar_stacked:
            data['options']['scales'] = {
                'xAxes': [{
                    'stacked': True,
                }],
                'yAxes': [{
                    'stacked': True
                }]
            }
            for ds in data['data']['datasets']:
                if 'stack' not in ds:
                    ds['stack'] = 'Stack 0'

        if len(data['data']['datasets']) == 1:
            data['options']['legend'] = {
               'display': False,
            }
        return data
