# -*- coding: utf-8 -*-
# Part of SnepTech See LICENSE file for full copyright and licensing details.##
##################################################################################

{
    'name': "Zoho Mail Fix",
    'summary': "fix the zoho outgoing mail server issue.",
    'sequence':1,
    "price": '19.99',
    "currency": 'USD',
       
    'description':""" 
       This module is aim to fix zoho mail server relaying issue - like mail sender's email must be same as outgoing mail server email.
        
    """,
    'live_test_url':"https://youtu.be/XFofqLoa4ic",
    'category': '',
    'version': '12.0.0.1',
    'license': 'AGPL-3',
    'author': 'SnepTech',
    'website': 'https://www.sneptech.com',
    
    'depends': ['base'],

    'data': [
        'views/ir_mail_server_view.xml',
    ],
            
    'application': True,
    'installable': True,
    'auto_install': False,
    "images":['static/description/Banner.png'],    
}
