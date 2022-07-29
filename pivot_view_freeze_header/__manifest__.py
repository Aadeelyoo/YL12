# -*- coding: utf-8 -*-
{
    'name': "Fixed Pivot View Header",
    'version': '1.0.2',
    'license': 'OPL-1',
    'author': "ERP Labz",
    'maintainer': 'ERP Labz',
    'category': 'Web',
    'summary': """
        Added the freeze header for pivot view, Fixed the pivot view header and the first column.""",
    'description': """
        Added the freeze header for pivot view, Fixed the pivot view header and the first column.
        Odoo Pivot View 
        Pivot View
        Freeze Pivot View
        Freeze Pivot View Header
        Fixed Pivot View Header 
        Fixed Pivot View Column 
        Odoo Freeze Pivot View
        Odoo Sticky Header 
        Pivot View Sticky Header 
        Fixed Header 

    """,
    'website': "http://erplabz.com/",
    'depends': ['base', 'web', 'base_setup'],
    'data': [
        'data/pivot_view_state_config_parameter.xml',
        'views/assets.xml',
        'views/inherit_config.xml',
    ],
    'images': ['static/description/banner.png'],
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'price': '30',
    'currency': 'EUR',
    'application': True,
    'auto_install': False,
}
