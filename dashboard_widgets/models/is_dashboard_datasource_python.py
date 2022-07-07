from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as safe_eval

import datetime
import dateutil

IS_ODOO_VERSION_BEFORE_v12 = True


class DashboardWidget(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    datasource = fields.Selection(selection_add=[
        ('python', 'Python'),
    ])

    query_1_config_python_domain = fields.Text()
    query_2_config_python_domain = fields.Text()

    query_1_config_python = fields.Text("Python Code")

    def get_run_python_count_eval_context(self):
        return {
            'dashboard': self,

            'model': self.query_1_config_model_id.model,
            'date_range_start': self.query_1_config_date_range_start or self.query_1_config_datetime_range_start,
            'date_range_end': self.query_1_config_date_range_end or self.query_1_config_datetime_range_end,

            'dom1': self.query_1_config_python_domain,
            'dom2': self.query_2_config_python_domain,

            'env': self.env,
            'datetime': datetime,
            'dateutil': dateutil
        }

    def run_python_count(self):
        can_write = self.check_access_rights('write', raise_exception=False)

        code = self.query_1_config_python
        locals = {}
        eval_context = self.get_run_python_count_eval_context()
        if code:
            try:
                safe_eval(code, eval_context, locals, mode="exec", nocopy=True)
            except Exception as ex:
                if can_write:
                    self.query_1_error = "{}".format(ex)

            self.count = locals.get('count', 0)
            self.total = locals.get('total', 0)
            self.query_1_config_python_domain = locals.get('dom1', 0)
            self.query_2_config_python_domain = locals.get('dom2', 0)
