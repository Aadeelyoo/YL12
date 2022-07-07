# -*- coding: utf-8 -*-
{
    'name': 'Dashboard Widgets',
    'category': 'Extra Tools',
    'website': 'https://www.inspiredsoftware.com.au',
    'summary': 'Dashboard widgets to be displayed in kanban views',
    'version': '10.0.11.0',
    'description': """
        """,
    'author': 'Inspired Software Pty Ltd',
    'live_test_url': 'https://www.inspiredsoftware.com.au/r/YTb',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'views/assets.xml',
        'views/dashboard.xml',
        'views/dashboard_preview.xml',
        'views/dashboard_notes.xml',
        'views/dashboard_widget_cache.xml',
        'views/dashboard_widget_config_date.xml',
        'views/dashboard_widget_card.xml',
        'views/dashboard_widget_datasource_python.xml',
        'views/dashboard_widget_graph.xml',
        'views/dashboard_widget_html.xml',
        'views/dashboard_widget_star.xml',
        'views/dashboard_widget_tag.xml',
        'views/dashboard_email.xml',
        'views/dashboard_sound.xml',
        'templates/dashboard_email.xml',
        'wizard/dashboard_wizard_create.xml',
        'data/cron.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/kanban_templates.xml',
    ],
    'images': [
        'static/description/dashboard01.png'
    ],
    'installable': True,
    'application': True,

    'licence': 'OPL-1',
    'support': 'appsupport@inspiredsoftware.com.au',
    'price': '400',
    'currency': 'USD',
}
