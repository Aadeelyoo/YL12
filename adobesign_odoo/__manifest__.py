# -*- coding: utf-8 -*-
{
    'name': "Solevo Adobe Sign Connector",

    'summary': """Technical module to connect Adobe Sign with ODOO""",

    'author': "Solevo inc.",
    'website': "https://www.solevo.ca",
    'category': 'Document Management',

    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    'license': 'OPL-1',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/message_wizard.xml',
        'views/res_company.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'OPL-1',

}
