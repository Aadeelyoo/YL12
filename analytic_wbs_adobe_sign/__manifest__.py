# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Solevo Analytics wbs Adobe Sign',
    'author': "Solevo inc.",
    'version': '12,0.1.0.0',
    'website' : 'https://www.solevo.ca',
    'category': 'Hidden/Dependency',

    'depends': ['base', 'analytic_wbs', 'analytic_wbs_batch', 'adobesign_odoo', 'pikepdf_merge'],
    'description': """
Module for defining analytic_wbs accounting object.
===============================================

In OpenERP, analytic_wbs_adobe_sign is responsible to process documents for signature and retrieve
information using adobesign_odoo.
Models Included:
1. tci
2. tci.batch
    """,
    'data': [
        'report/report.xml',
        'views/tci_view.xml',
        'views/tci_batch_view.xml'
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,

}
