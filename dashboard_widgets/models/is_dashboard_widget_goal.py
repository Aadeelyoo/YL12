from odoo import models, fields, api

from datetime import datetime, date, time, timedelta
import json

IS_ODOO_VERSION_BEFORE_v12 = False

class DashboardWidgetGoal(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    # TODO: Is anyone using goal_total?
    goal_count = fields.Float(string="Standard Goal (1)")
    goal_total = fields.Float(string="Standard Goal (2)")

    goal_1_is_greater_than = fields.Boolean(string="Goal is greater than", default=True, oldname='goal_is_greater_than')
    goal_1_line_ids = fields.One2many(comodel_name="is.dashboard.widget.goal", inverse_name="dashboard_widget_1_id", oldname='goal_line_ids')
    goal_2_is_greater_than = fields.Boolean(string="Goal is greater than", default=False)
    goal_2_line_ids = fields.One2many(comodel_name="is.dashboard.widget.goal", inverse_name="dashboard_widget_2_id")

    current_goal_date_start = fields.Date(string="Goal Start", compute='compute_current_goal_count')
    current_goal_date_end = fields.Date(string="Goal End", compute='compute_current_goal_count')

    def get_1_goal_for_date(self, current_date, current_goal_value_only=False):
        return self._get_goal_for_date(
            self.goal_1_line_ids,
            self.goal_count,
            current_date,
            current_goal_value_only=current_goal_value_only,
        )

    def get_2_goal_for_date(self, current_date, current_goal_value_only=False):
        return self._get_goal_for_date(
            self.goal_2_line_ids,
            self.goal_total,
            current_date,
            current_goal_value_only=current_goal_value_only,
        )

    def _get_goal_for_date(self, lines, default_goal, current_date, current_goal_value_only=False):
        if not isinstance(current_date, date):
            # TODO: Do we need to do anything with TZ here?
            current_date = fields.Date.from_string(current_date)

        current_goal = lines.filtered(lambda b: b.date and fields.Date.from_string(b.date) <= current_date).sorted(key='date', reverse=True)
        current_goal = current_goal[0] if current_goal else False

        if current_goal_value_only:
            return current_goal.goal if current_goal else default_goal

        if current_goal:
            next_goal = lines.filtered(lambda b: b.date and fields.Date.from_string(b.date) > fields.Date.from_string(current_goal.date)).sorted(key='date')
            next_goal = next_goal[0] if next_goal else False
        else:
            next_goal = False

        return current_goal, next_goal

    @api.depends(
        'goal_1_line_ids',
        'goal_1_line_ids.date',
        'goal_1_line_ids.goal',
    )
    def compute_current_goal_count(self):
        for rec in self:
            today = date.today()
            current_goal, next_goal = rec.get_1_goal_for_date(today)

            rec.current_goal_count = current_goal.goal if current_goal else rec.goal_count
            # TODO migrate to use the goal_2_line_ids rec.current_goal_total = current_goal.goal_total if current_goal else rec.goal_count

            rec.current_goal_date_start = current_goal.date if current_goal else False
            rec.current_goal_date_end = next_goal.date if next_goal else False

    @api.depends(
        'goal_2_line_ids',
        'goal_2_line_ids.date',
        'goal_2_line_ids.goal',
    )
    def compute_current_goal_total(self):
        for rec in self:
            today = date.today()
            current_goal, next_goal = rec.get_2_goal_for_date(today)

            rec.current_goal_total = current_goal.goal if current_goal else rec.goal_total

            # rec.current_goal_date_start = current_goal.date if current_goal else False
            # rec.current_goal_date_end = next_goal.date if next_goal else False
