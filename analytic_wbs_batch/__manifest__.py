# -*- coding: utf-8 -*-
{
    'name': "analytic_wbs_batch",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Solevo inc.",
    'website': "http://www.solevo.ca",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'analytic_wbs', 'evosoft_report_template'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/batch_views.xml',
        'views/tci_views.xml',
        'report/report.xml',
        'report/table_templates.xml',
        'report/report_header_footer.xml',
        'report/module_report.xml',
        'report/report_email_template.xml',
        'wizard/approval_feedback_view.xml',
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}