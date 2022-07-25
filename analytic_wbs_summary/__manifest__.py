# -*- coding: utf-8 -*-
{
    'name': "analytic_wbs_summary",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'analytic_wbs', 'dashboard_view'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/cost_control_views.xml',
        'views/analytic_project_wbs_view.xml',
        'views/templates.xml',
        'wizards/report_record_wizard_view.xml',
        'views/project_control_records_view.xml',
        'views/project_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}