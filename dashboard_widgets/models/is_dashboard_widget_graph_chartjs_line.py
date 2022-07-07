from odoo import api, fields, models

from collections import OrderedDict


class DashboardWidgetGraph(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    def get_dataset_for_goal_1(self, dates, labels=None):
        if dates:
            return {
                'label': self.chart_1_goal_config_title,
                'data': [self.get_1_goal_for_date(date, current_goal_value_only=True) if date else 0 for date in dates],
                'domains': False,
                'date_start': False,
                'action_id': False,
            }
        elif labels:
            return {
                'label': self.chart_1_goal_config_title,
                'data': [self.goal_count for label in labels],
                'domains': False,
                'date_start': False,
                'action_id': False,
            }

    def get_dashboard_data(self):
        if self.display_mode != 'graph' or self.graph_type != 'line':
            return super(DashboardWidgetGraph, self).get_dashboard_data()

        data1, color1, area1, title1 = self.chart_get_data_query_1()
        # TODO: Allow data2 set to work
        # data2, color2, area2, title2 = self.chart_get_data_query_2()

        if not data1:
            return False

        data = {
            'type': 'line',
            'show_values_on_graph': self.show_values_on_graph,
            'data': data1,
            'options': {},
        }

        if self.query_1_config_enable_goal and (data1['dates'] or self.goal_count):
            ds = self.get_dataset_for_goal_1(data1['dates'], data1['labels'])

            ds['fill'] = self.chart_1_goal_config_area

            if self.chart_1_goal_config_color:
                ds['pointColor'] = self.chart_1_goal_config_color
                ds['pointBorderColor'] = self.chart_1_goal_config_color
                ds['pointBackgroundColor'] = self.chart_1_goal_config_color
                ds['borderColor'] = self.chart_1_goal_config_color
                ds['backgroundColor'] = self.chart_1_goal_config_color

            data['data']['datasets'].append(ds)

        if data['data']['datasets']:
            for ds in data['data']['datasets']:
                if 'fill' not in ds:
                    ds['fill'] = area1

        # TODO: Enable stacking line graphs
        # self.graph_1_bar_stacked
        # if True:
        #     data['options']['scales'] = {
        #         'yAxes': [{
        #             'stacked': True,
        #         }],
        #     }

        if len(data['data']['datasets']) == 1:
            data['options']['legend'] = {
                'display': False,
            }

        return data
