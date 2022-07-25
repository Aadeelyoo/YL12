# -*- coding: utf-8 -*-
{
    'name': "Project Cost Report",
    'summary': """Project Cost Report""",
    'author': "Odoo",
    'website': "http://www.odoo.com",
    'category': 'Project Management',
    'version': '12.0.8',
    'depends': ['base','analytic_wbs_summary'],
    'data': [
        'report/module_report.xml',
        'report/template.xml',
        'analytics_wbs/analytic_wbs.xml',
    ],
    'demo': [
    ],
    
}
