# -*- coding:utf-8 -*-
########################################################################################
########################################################################################
##                                                                                    ##
##    OpenERP, Open Source Management Solution                                        ##
##    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved       ##
##                                                                                    ##
##    This program is free software: you can redistribute it and/or modify            ##
##    it under the terms of the GNU Affero General Public License as published by     ##
##    the Free Software Foundation, either version 3 of the License, or               ##
##    (at your option) any later version.                                             ##
##                                                                                    ##
##    This program is distributed in the hope that it will be useful,                 ##
##    but WITHOUT ANY WARRANTY; without even the implied warranty of                  ##
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                   ##
##    GNU Affero General Public License for more details.                             ##
##                                                                                    ##
##    You should have received a copy of the GNU Affero General Public License        ##
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.           ##
##                                                                                    ##
########################################################################################
########################################################################################

from odoo import api, models, fields
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import Warning


class SolevoTciReport(models.AbstractModel):
    _name = 'report.analytic_wbs.solevo_tci_report_id'

    def get_approval_ids(self, res_id):
        if res_id:
            mail_apporvers = self.env['mail.approvers'].search([('res_model', '=', 'tci'), ('res_id', '=', res_id.id)])
            return mail_apporvers

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['tci'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'tci',
            'docs': docs,
            'get_approval_ids': self.get_approval_ids,
        }
