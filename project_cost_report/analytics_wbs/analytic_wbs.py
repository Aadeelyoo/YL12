# #-*- coding:utf-8 -*-

from datetime import date
from datetime import date, timedelta
from odoo import api, models, fields

class AnalyticsWbsRecordExtend(models.Model):
	_inherit = "analytic.wbs.record"
	
	def generate_report(self):
		return self.env.ref('project_cost_report.report_for_project_cost').report_action(self)
	