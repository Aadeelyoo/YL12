# -*- coding: utf-8 -*-
##############################################################################
#
#    Solevo inc.
#    Copyright (C) 2019-TODAY Solevo(<https://www.solevo.ca>).
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': "Solevo Odoo Debranding",
    'version': "12.0.1.0.1",
    'summary': """Debrand Odoo""",
    'description': """Debrand Odoo""",
    'author': "Solevo",
    'company': "Solevo inc",
    'website': "https://solevo.ca/",
    'category': 'Tools',
    'depends': ['base', 'im_livechat', 'website'],
    'data': [
        'views/views.xml',
        'data/data.xml',
        'data/auth_signup_data.xml'
    ],
    'demo': [],
    'qweb': ["static/src/xml/base.xml"],
    'images': ['static/description/solevo_logo.png'],
    'license': "LGPL-3",
    'installable': True,
    'application': False
}