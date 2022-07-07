# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Solevo Adobe Merge Connector',
    'author': "Solevo inc.",
    'version': '12,0.1.0.0',
    'website' : 'https://www.solevo.ca',
    'category': 'Hidden/Dependency',
    'depends': ['base'],
    'description': """
Module for defining adobe_merge object.
===============================================

In OpenERP, adobe_merge can be used to add functionality to merge pdf documents via adobe.
    """,
    "external_dependencies" : {"python" : ["jws"]},
    'installable': True,
    'auto_install': False,
}
