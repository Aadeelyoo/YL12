from odoo import models, fields, api, _
from . import adobesign_api as adobe
import requests
import json
from odoo.exceptions import UserError, ValidationError
from openerp.osv import osv
import time
from odoo import http
from odoo.http import request
import datetime, os

import base64


class AdobeSignAgreement(models.Model):
    _name = 'adobesign.agreement'

    name = fields.Char(string="Document Name", readonly="1")
    agreement_id = fields.Char(string="Agreement Id", readonly="1")
    customer_id = fields.Many2one('res.partner', 'Customer')
    agreement_status = fields.Char(string="Status")

    unsigned_file_data_adobesign = fields.Many2many('ir.attachment', 'unsignedadobeagreement_ir_attachments_rel',
                                                    'unsignedadobeagreement_id', 'attachment_id',
                                                    'Unsigned Attachments')

    upload_file_data_adobesign = fields.Many2many('ir.attachment', 'adobeagreement_ir_attachments_rel',
                                                  'adobeagreement_id', 'attachment_id', 'Signed Attachments')


class AdobeSignCredentials(models.Model):
    _name = 'adobe.credentials'

    name = fields.Char(string='Adobe Sign Account Name', required=True)

    odoo_url = fields.Char(string="ODOO URL",
                           help="Write down the complete base url of your ODOO including the http/https", required=True)

    access_token = fields.Char(string='Access Token', readonly=True)
    refresh_token = fields.Char(string='Refresh Token')
    access_token_time = fields.Datetime(string='Token Generation Time')
    expire_in = fields.Char('Expires IN', readonly=True)
    client_id = fields.Char(string='Client Id', required=True)
    client_secret = fields.Char(string='Secret Id', required=True)
    api_access_point = fields.Char(string='Api Access Point')
    redirect_url = fields.Char(string='Redirect url', required=True)
    login_url = fields.Char('Login URL', compute='_compute_url', readonly=True)
    url = fields.Char(string='url')
    code = fields.Char(string='code')
    adobesign_domain = fields.Char("AdobeSign Domain", required=True)
    current_user = fields.Many2one('res.users', 'Current User', default=lambda self: self.env.user)

    def _compute_url(self):
        authorize_url = "https://{0}/public/oauth/v2".format(self.adobesign_domain)

        redirect_url = 'redirect_uri=' + str(self.redirect_url) + '&'
        client_id = 'client_id=' + str(self.client_id) + '&'
        authorize_url = str(authorize_url) + '?'
        scope = "scope=user_login:account+agreement_write:account+agreement_send:account+widget_write:account" \
                "+library_write:account+library_read:account+agreement_read:account "
        self.login_url = authorize_url + redirect_url + client_id + 'response_type=code&' + scope  # + state

    def get_code(self):
        return {'type': 'ir.actions.act_url',
                'url': self.login_url,
                'target': 'self',
                'res_id': self.id,
                }

    def test_connection(self):

        try:
            if not self.client_id or not self.redirect_url or not self.client_secret:
                raise osv.except_osv(_("Error!"), (_(
                    "Please give Credentials!")))
            else:
                self.env.user.client_id = self.client_id
                self.env.user.redirect_url = self.redirect_url
                self.env.user.client_secret = self.client_secret
                self.env.user.name = self.name
                self.env.user.api_access_point = self.adobesign_domain
                self.env.user.api_access_point = self.api_access_point
                self.env.cr.commit()

                context = dict(self._context)
                context['message'] = 'Successfull!'
                return self.message_wizard(context)

        except Exception as e:
            raise ValidationError(_((e)))

    def generate_token(self):
        self.code = self.env.user.code
        try:
            if not self.code:
                raise UserError(_('Please enter ODOO url'))

            if not self.client_id or not self.redirect_url or not self.client_secret:
                raise osv.except_osv(_("Error!"), (_("Please  add credentials!")))

            else:
                header = {'Content-Type': 'application/x-www-form-urlencoded'}
                response = requests.post("https://{0}//oauth/v2/token".format(self.adobesign_domain),
                                         data='grant_type=authorization_code&code=' + self.code + '&redirect_uri=' + self.redirect_url + '&client_id=' + self.client_id + '&client_secret=' + self.client_secret,
                                         headers=header).content
                response = json.loads(response.decode('utf-8'))
                self.access_token = response['access_token']
                self.refresh_token = response['refresh_token']
                self.expire_in = int(round(time.time() * 1000))
                self.env.user.expire_in = self.expire_in
                self.env.user.code = self.code
                self.env.user.access_token = self.access_token
                self.env.user.refresh_token = self.refresh_token
                self.env.user.access_token_time = None
                self.env.cr.commit()

                context = dict(self._context)
                context['message'] = 'Token Generated!'
                return self.message_wizard(context)

        except Exception as e:
            raise ValidationError(e)

    def message_wizard(self, context):
        return {
            'name': ('Success'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context

        }

class AdobeSignUser(models.Model):
    _inherit = 'res.users'

    client_id = fields.Char(string='Client Id', required=True)
    client_secret = fields.Char(string='Secret Id', required=True)
    api_access_point = fields.Char(string='Api Access Point')
    redirect_url = fields.Char(string='Redirect url', required=True)
    access_token = fields.Char(string='Access Token', readonly=True)
    refresh_token = fields.Char(string='Refresh Token')
    access_token_time = fields.Datetime(string='Token Generation Time')
    expire_in = fields.Char('Expires IN', readonly=True)
    code = fields.Char(string='code')
