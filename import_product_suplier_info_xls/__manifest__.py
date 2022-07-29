# coding: utf-8


{
    'name': 'Import Product Suplier',
    'version': '12.0.0.1',
    'license': 'AGPL-3',
    'category': 'Sales,Purchase',
    'summary': "Import a product and suplier info",
    'depends': ['base',
                'web',
                'product',
                'purchase'
                ],
    'data': [
        'wizard/import_suplier_info.xml',

    ],

    'installable': True,
    'application': True,

}
