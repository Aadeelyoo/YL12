# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import datetime


class AdobeSignOdoo(http.Controller):
    @http.route(['/echosign/<int:template_id>'], auth='public')
    def index(self, template_id, **kw):
        if 'status_code' in kw:
            if not kw['status_code'] == '200':
                return "Error Generating Tokens"
            api_access_point = kw['api_access_point']
            api_access_point = api_access_point.replace('/oauth/token?','')

            ### editing ####
            access_token = kw['access_token']
            refresh_token = kw['refresh_token']
            client_id = kw['client_id']
            client_secret = kw['clientSecret']
            api_access_point = api_access_point
            access_token_time = datetime.datetime.now()

            purchase_order_line_vals = {
                'access_token': str(access_token),
                'refresh_token': str(refresh_token),
                'client_id': str(client_id),
                'client_secret': str(client_secret),
                'api_access_point': str(api_access_point),
                'access_token_time': access_token_time,
            }

            env_token = request.env['adobe.credentials']
            env_token.sudo().browse(int(template_id)).write(purchase_order_line_vals)
            return "Tokens generated successfully and have been saved. " \
                   "Please close this window and go back to ODOO to send the document to Adobe Sign"

        if 'error' in kw:
            return kw['error_description']

    @http.route('/code', auth='public')
    def code(self, **kw):
        print(kw['code'])
        print(request.env.context)
        auth_code = kw['code']
        c_user = request.env['res.users'].search([('id', '=', request.env.context['uid'])])
        c_user.code = auth_code

