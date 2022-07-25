# -*- coding: utf-8 -*-
{
    'name': "Task Forecast grid view",
    'summary': "Task Forecast Grid View",
    'description': """
* Activate grid view for task forecast
    """,
    'version': '12.0.0.1',
    'website': 'http://www.solevo.ca',
    'author': 'Solevo inc.',
    'depends': ['generic_grid', 'analytic_wbs'],
    'data': [
        'views/project_task_forecast_view.xml',
        'views/project_task_view.xml',
        'views/hr_employee_view.xml',
        'views/purchase_order_view.xml',
        'views/project_control_view.xml',
        'views/analytic_project_wbs_view.xml',
        'actions/actions.xml',
    ],
    'auto_install': True,
}
