# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Solevo Pike PDF Merge',
    'author': "Solevo inc.",
    'version': '12,0.1.0.0',
    'website' : 'https://www.solevo.ca',
    'category': 'Hidden/Dependency',
    'depends': ['base'],
    'description': """
Module for merging PDF from stack array.
===============================================

In OpenERP, process_from_stack can be used to add functionality to merge pdf documents.
    """,
    "external_dependencies" : {"python" : ["pikepdf"]},
    'installable': True,
    'auto_install': False,
}
