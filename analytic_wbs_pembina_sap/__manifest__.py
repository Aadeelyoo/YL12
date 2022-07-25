# -*- coding: utf-8 -*-
{
    'name': "analytic_wbs_pembina_sap",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Solevo inc.",
    'website': "http://www.solevo.ca",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','analytic_wbs','analytic_wbs_default_product','auditlog'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sap_actuals_dump_view.xml',
        'views/sap_vendor_dump_view.xml',
        'views/sap_open_po_dump_view.xml',
        'views/sap_gr_dump_view.xml',
        'views/workflow_invoice_dump_view.xml',
        'views/sap_view.xml',
        'views/purchase_order_view.xml',
        'views/tci_view.xml',
        'views/vendor_view.xml',
        'views/analytic_wbs_project_view.xml',
        'views/menus_view.xml',
        'views/templates.xml',
        'data/auditlog_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}