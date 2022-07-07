{
    'name': "Approval Mixin",
    'description': "Module for approval in msg threads",
    'author': 'Solevo,Ehtisham Faisal',
    'category': 'mail',
    'version': '12.0.3',
    'application': True,
    #'depends': ['base', 'mail','sale_management'],
    'depends': ['base', 'mail', 'adobesign_odoo'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/cron.xml',
        'views/adobe_agreements.xml',
        'views/mail_mix_view.xml',
        'views/mail_approvers_view.xml',
        'report/report.xml',
        'report/module_report.xml',
    ],
    'qweb': [
        "static/src/xml/mail_activity_template.xml",
    ],
}