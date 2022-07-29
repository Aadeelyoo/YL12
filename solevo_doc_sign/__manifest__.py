# -*- coding: utf-8 -*-
{
    'name': "solevo_doc_sign",

    'summary': """
        Allow yo add multiple signatures to a record""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Solevo",
    'website': "https://solevo.ca",

    'category': 'Tool',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'web_widget_digitized_signature'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}