from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AnalyticWbsRecordWizard(models.TransientModel):
    _name = 'analytic.wbs.record.wizard'
    _description = 'Project Report Recording Wizard'

    name = fields.Char(string='Name')
    project_id = fields.Many2one('project.project', string='Project', required=True)
    report_end_period = fields.Date(string='Period End Date', required=True, default=fields.Date.today)
    comparison_record_id = fields.Many2one('analytic.wbs.record', string='Comparison Report', required=False)
    record_type = fields.Selection([
        ('mend', 'Month End'),
        ('temp', 'Temporary Record'),
    ], string='Record Type', help="Type is used to group the records in the reports.", required=True, default='temp')

    is_active = fields.Boolean('Active', default=True)

    @api.depends('project_id')
    def get_default_comparaison_rec(self):
        print('allo')
        last_month_end_rec_ids = self.env['analytic.wbs.record'].search([('project_id', '=', self.project_id),
                                                                         ('record_type', '=', 'mend'),
                                                                         ('is_active', '=', True)])

    def create_report_record(self):
        AnalyticWbsRecord = self.env['analytic.wbs.record']

        # Verify if the another month end report exist for the same period and project, if it does, do not recort
        current_records = AnalyticWbsRecord.search([('report_end_period', '=', self.report_end_period),
                                                    ('record_type', '=', 'mend'),
                                                    ('is_active', '=', True),
                                                    ('project_id', '=', self.project_id.id)])
        if current_records and self.record_type == 'mend':
            raise UserError(
                _('An active month end report already exist for this project.'
                  ' Please de-activate the existing project report to be able to create a new month one.'))

        report_lines = self.env['analytic_wbs_cost_report'].search([('project_id', '=', self.project_id.id)])

        #get report period month
        rep_period = str(self.report_end_period.strftime('%Y-%m'))
        print(rep_period)

        new_lines = []
        for line in report_lines:
            if line.data_col_group == '50-Incurred Current':
                data_col = rep_period
            else:
                data_col = line.data_col

            vals = {
                'record_data_timeline': 'current',
                #'record_id': new_record.id,
                'po_id': line.po_id.id,
                'employee_id': line.employee_id.id,
                'partner_id': line.partner_id.id,
                'project_wbs_id': line.project_wbs_id.id,
                'wbs_id': line.wbs_id.id,
                'project_id': line.project_id.id,
                'task_id': line.task_id.id,
                'data_col': data_col,
                'data_col_group': line.data_col_group,
                'rep_uid': line.rep_uid,
                'rep_name': line.rep_name,
                'rep_uid_type': line.rep_uid_type,
                #'data_type': line.data_type,
                'amount': line.amount,
                'past_amount': line.past_amount,
                'variance': line.variance,
            }
            new_lines.append(vals)
            #new_lines = self.env['analytic.wbs.record.line'].create(vals)

        new_record = AnalyticWbsRecord.create({
            "name": self.name,
            "report_end_period": self.report_end_period,
            "project_id": self.project_id.id,
            "is_active": self.is_active,
            "record_type": self.record_type,
        })

        # add new lines to new record
        for line in new_lines:
            line['record_id'] = new_record.id
            new_line = self.env['analytic.wbs.record.line'].create(line)
