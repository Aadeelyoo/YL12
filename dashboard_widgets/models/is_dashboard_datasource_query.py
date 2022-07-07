from odoo import api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval as safe_eval

from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import rrule
import pytz

IS_ODOO_VERSION_BEFORE_v12 = False


DATE_RANGE_TYPES = [
    ('today', 'Today'),
    ('yesterday', 'Yesterday'),
    ('this_week_monday_friday', 'This Week (Monday-Friday)'),
    ('this_week_monday_sunday', 'This Week (Monday-Sunday)'),
    ('this_week_sunday_saturday', 'This Week (Sunday-Saturday)'),
    ('this_month', 'This Month'),
    ('this_year', 'This Year'),
    ('last_x_days', 'Last X Days'),
    ('last_x_months', 'Last X Months'),
    ('last_x_years', 'Last X Years'),
    ('last_month', 'Last Month'),
    ('last_month_to_date', 'Last Month To Date'),
    ('last_year', 'Last Year'),
    ('last_year_to_date', 'Last Year To Date'),
    ('custom', 'Custom'),
    ('current_goal', 'Current Goal'),
]

if IS_ODOO_VERSION_BEFORE_v12:
    AGGREGATE_OPERATOR_TYPES = []

else:
    AGGREGATE_OPERATOR_TYPES = [
        # https://www.postgresql.org/docs/current/functions-aggregate.html
        ('avg', 'Average'),
        ('count', 'Count'),
        ('max', 'Max'),
        ('min', 'Min'),
        ('sum', 'Sum'),

        # < V12
        # ('day', 'Day'),
        # ('week', 'Week'),
        # ('month', 'Month'),
        # ('quarter', 'Quarter'),
        # ('year', 'Year'),
    ]


class DashboardDatasourceQuery(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    datasource = fields.Selection(default="query", selection_add=[('query', "Query")])

    query_1_error = fields.Text(string="Error", readonly=True)
    query_1_error_date = fields.Text(string="Date Range Error", readonly=True)

    query_1_config_domain = fields.Text(oldname='count_domain', default='[]')
    query_1_config_domain_widget = fields.Char(compute="compute_domain_1_widget", inverse="inverse_domain_1_widget")
    query_1_config_domain_use_widget = fields.Boolean(oldname='use_domain_widget', default=True)
    query_1_config_model_id = fields.Many2one('ir.model', string="Record Type (1)", oldname="model_id")
    query_1_config_model_id_name = fields.Char(related="query_1_config_model_id.model")
    query_1_config_measure_field_id = fields.Many2one('ir.model.fields', oldname='query_1_config_aggregate_field_id', string="Aggregate Field (1)", help="Field to use to aggregate domain results. If empty will default to count")
    query_1_config_measure_operator = fields.Selection(selection=AGGREGATE_OPERATOR_TYPES, help="Operator to use on each group for aggregate_field. eg. sum, max, min, avg", oldname='query_1_config_aggregate_operator')
    query_1_config_measure_operator_supported = fields.Boolean(compute='compute_query_1_config_measure_operator_supported')

    query_1_config_date_range_type = fields.Selection(selection=DATE_RANGE_TYPES, oldname="auto_filter_date_range")
    query_1_config_date_range_custom_start = fields.Date(string="Custom Start (1)")
    query_1_config_date_range_custom_end = fields.Date(string="Custom End (1)")
    query_1_config_datetime_range_custom_start = fields.Datetime(string="Custom Start (1)", oldname="custom_date_start")
    query_1_config_datetime_range_custom_end = fields.Datetime(string="Custom End (1)", oldname="custom_date_end")
    query_1_config_date_range_field_id = fields.Many2one('ir.model.fields', oldname='config_date_range_field_id', string="Aggregate Field", help="Field to use to aggregate domain results. If empty will default to count")
    query_1_config_date_range_x = fields.Integer(default=0, oldname="auto_filter_date_range_x")
    query_1_config_date_range_x_label = fields.Char(compute="compute_query_1_auto_filter_date_range_x_type")

    query_1_config_date_is_datetime = fields.Boolean(string="Is Datetime (1)", compute="compute_query_1_config_date_range")
    query_1_config_date_range_start = fields.Date(string="Query Start Date (1)", compute="compute_query_1_config_date_range")
    query_1_config_date_range_end = fields.Date(string="Query End Date (1)", compute="compute_query_1_config_date_range")
    query_1_config_datetime_range_start = fields.Datetime(string="Query Start Datetime (1)", compute="compute_query_1_config_date_range")
    query_1_config_datetime_range_end = fields.Datetime(string="Query End Datetime (1)", compute="compute_query_1_config_date_range")

    query_1_config_enable_goal = fields.Boolean(string="Enable Goal (1)", oldname='has_goal')

    @api.depends('query_1_config_measure_field_id')
    def compute_query_1_config_measure_operator_supported(self):
        for rec in self:
            rec.query_1_config_measure_operator_supported = not IS_ODOO_VERSION_BEFORE_v12 and rec.query_1_config_measure_field_id

    @api.depends(
        'query_1_config_model_id', 'query_1_config_date_range_field_id',
        'query_1_config_date_range_type',
        'query_1_config_date_range_custom_start', 'query_1_config_date_range_custom_end',
        'current_goal_date_start', 'current_goal_date_end',
        'query_1_config_date_range_x',
        'config_id.config_date_start', 'config_id.config_date_end',
    )
    def compute_query_1_config_date_range(self):
        can_write = self.check_access_rights('write', raise_exception=False)
        for rec in self:
            if can_write:
                rec.query_1_error_date = False

            start, end, is_datetime, error = rec.get_date_range_values(
                rec.query_1_config_model_id, rec.query_1_config_date_range_field_id,
                rec.query_1_config_date_range_type,
                rec.query_1_config_date_range_custom_start, rec.query_1_config_date_range_custom_end,
                rec.query_1_config_datetime_range_custom_start, rec.query_1_config_datetime_range_custom_end,
                rec.current_goal_date_start, rec.current_goal_date_end,
                rec.query_1_config_date_range_x,
                rec.config_id.config_date_start, rec.config_id.config_date_end,
            )

            if IS_ODOO_VERSION_BEFORE_v12:
                if is_datetime:
                    start = fields.Datetime.to_string(start)
                    end = fields.Datetime.to_string(end)
                else:
                    start = fields.Date.to_string(start)
                    end = fields.Date.to_string(end)

            rec.query_1_config_date_is_datetime = is_datetime

            if is_datetime:
                rec.query_1_config_datetime_range_start = start
                rec.query_1_config_datetime_range_end = end
            else:
                rec.query_1_config_date_range_start = start
                rec.query_1_config_date_range_end = end

            if can_write:
                rec.query_1_error_date = error

    @api.depends('query_1_config_date_range_type')
    def compute_query_1_auto_filter_date_range_x_type(self):
        for rec in self:
            rec.query_1_config_date_range_x_label = rec.get_query_config_date_range_x_label(rec.query_1_config_date_range_type)

    def get_query_1_domain(self):
        self.sudo().compute_query_1_config_date_range()
        return self._get_dom(
            self.query_1_config_domain or self.query_1_config_python_domain,
            self.query_1_config_date_range_start or self.query_1_config_datetime_range_start,
            self.query_1_config_date_range_end or self.query_1_config_datetime_range_end,
            self.query_1_config_date_range_field_id,
        )

    @api.depends('query_1_config_domain', 'query_1_config_domain_use_widget')
    def compute_domain_1_widget(self):
        for rec in self:
            rec.query_1_config_domain_widget = rec.query_1_config_domain if rec.query_1_config_domain_use_widget else []

    @api.onchange('query_1_config_domain_widget', 'query_1_config_domain_widget')
    def inverse_domain_1_widget(self):
        for rec in self:
            rec.query_1_config_domain = rec.query_1_config_domain_widget if rec.query_1_config_domain_use_widget else rec.query_1_config_domain


    query_2_error = fields.Text(string="Error", readonly=True)
    query_2_error_date = fields.Text(string="Date Range Error", readonly=True)

    query_2_config_domain = fields.Text(oldname='total_domain', default='[]')
    query_2_config_domain_widget = fields.Char(compute="compute_domain_2_widget", inverse="inverse_domain_2_widget")
    query_2_config_domain_use_widget = fields.Boolean(default=True)
    query_2_config_model_id = fields.Many2one('ir.model', string="Record Type (2)")
    query_2_config_model_id_name = fields.Char(related="query_2_config_model_id.model")
    query_2_config_measure_field_id = fields.Many2one('ir.model.fields',  string="Aggregate Field (2)", help="Field to use to aggregate domain results. If empty will default to count", oldname='query_2_config_aggregate_field_id')
    query_2_config_measure_operator = fields.Selection(selection=AGGREGATE_OPERATOR_TYPES, help="Operator to use on each group for aggregate_field. eg. sum, max, min, avg", oldname='query_2_config_aggregate_operator')
    query_2_config_measure_operator_supported = fields.Boolean(compute='compute_query_2_config_measure_operator_supported')

    query_2_config_date_range_type = fields.Selection(selection=DATE_RANGE_TYPES)
    query_2_config_date_range_custom_start = fields.Date(string="Custom Start (2)")
    query_2_config_date_range_custom_end = fields.Date(string="Custom End (2)")
    query_2_config_datetime_range_custom_start = fields.Datetime(string="Custom Start (2)")
    query_2_config_datetime_range_custom_end = fields.Datetime(string="Custom End (2)")
    query_2_config_date_range_field_id = fields.Many2one('ir.model.fields', string="Aggregate Field (2)", help="Field to use to aggregate domain results. If empty will default to count")
    query_2_config_date_range_x = fields.Integer(default=0)
    query_2_config_date_range_x_label = fields.Char(compute="compute_query_2_auto_filter_date_range_x_type")

    query_2_config_date_is_datetime = fields.Boolean(string="Is Datetime (2)", compute="compute_query_2_config_date_range")
    query_2_config_date_range_start = fields.Date(string="Query Start Date (2)", compute="compute_query_2_config_date_range")
    query_2_config_date_range_end = fields.Date(string="Query End Date (2)", compute="compute_query_2_config_date_range")
    query_2_config_datetime_range_start = fields.Datetime(string="Query Start Datetime (2)", compute="compute_query_2_config_date_range")
    query_2_config_datetime_range_end = fields.Datetime(string="Query End Datetime (2)", compute="compute_query_2_config_date_range")

    query_2_config_enable_goal = fields.Boolean(string="Enable Goal (2)")
    query_2_config_action_id = fields.Many2one(string="Action (2)", comodel_name='ir.actions.act_window')

    @api.depends('query_2_config_measure_field_id')
    def compute_query_2_config_measure_operator_supported(self):
        for rec in self:
            rec.query_2_config_measure_operator_supported = not IS_ODOO_VERSION_BEFORE_v12 and rec.query_2_config_measure_field_id

    @api.depends(
        'query_2_config_model_id', 'query_2_config_date_range_field_id',
        'query_2_config_date_range_type',
        'query_2_config_date_range_custom_start', 'query_2_config_date_range_custom_end',
        'query_2_config_datetime_range_custom_start', 'query_2_config_datetime_range_custom_end',
        'current_goal_date_start', 'current_goal_date_end',
        'query_2_config_date_range_x',
        'config_id.config_date_start', 'config_id.config_date_end',
    )
    def compute_query_2_config_date_range(self):
        for rec in self:
            start, end, is_datetime, error = rec.get_date_range_values(
                rec.query_2_config_model_id, rec.query_2_config_date_range_field_id,
                rec.query_2_config_date_range_type,
                rec.query_2_config_date_range_custom_start, rec.query_2_config_date_range_custom_end,
                rec.query_2_config_datetime_range_custom_start, rec.query_2_config_datetime_range_custom_end,
                rec.current_goal_date_start, rec.current_goal_date_end,
                rec.query_2_config_date_range_x,
                rec.config_id.config_date_start, rec.config_id.config_date_end,
            )

            if IS_ODOO_VERSION_BEFORE_v12:
                if is_datetime:
                    start = fields.Datetime.to_string(start)
                    end = fields.Datetime.to_string(end)
                else:
                    start = fields.Date.to_string(start)
                    end = fields.Date.to_string(end)

            rec.query_2_config_date_is_datetime = is_datetime

            if is_datetime:
                rec.query_2_config_datetime_range_start = start
                rec.query_2_config_datetime_range_end = end
            else:
                rec.query_2_config_date_range_start = start
                rec.query_2_config_date_range_end = end
            rec.sudo().write({'query_2_error_date': error})

    @api.depends('query_2_config_date_range_type')
    def compute_query_2_auto_filter_date_range_x_type(self):
        for rec in self:
            rec.query_2_config_date_range_x_label = rec.get_query_config_date_range_x_label(rec.query_2_config_date_range_type)

    @api.depends(
        'query_2_config_domain',
        'query_2_config_date_range_start',
        'query_2_config_date_range_end',
    )
    def get_query_2_domain(self):
        self.sudo().compute_query_2_config_date_range()
        return self._get_dom(
            self.query_2_config_domain or self.query_2_config_python_domain,
            self.query_2_config_date_range_start or self.query_2_config_datetime_range_start,
            self.query_2_config_date_range_end or self.query_2_config_datetime_range_end,
            self.query_2_config_date_range_field_id,
        )

    @api.depends('query_2_config_domain', 'query_2_config_domain_use_widget')
    def compute_domain_2_widget(self):
        for rec in self:
            rec.query_2_config_domain_widget = rec.query_2_config_domain if rec.query_2_config_domain_use_widget else []

    @api.onchange('query_2_config_domain_widget', 'query_2_config_domain_widget')
    def inverse_domain_2_widget(self):
        for rec in self:
            rec.query_2_config_domain = rec.query_2_config_domain_widget if rec.query_2_config_domain_use_widget else rec.query_2_config_domain

    def action_open_data_query_2(self):
        return self._action_open_data(
            self.query_2_config_model_id.model,
            action=self.query_2_config_action_id,
            domain=self.get_query_2_domain()
        )



    ######################################
    # COMMON FUNCTIONS FOR QUERY #1, #2, etc
    ######################################

    def get_group_by_tuple(self, field, aggregate_operator, date_only_aggregate=True):
        if not field:
            return False, False, False, False

        aggregate_operator_allowed = not date_only_aggregate or field.ttype in ['datetime', 'date']
        return (
            field.name,
            aggregate_operator if aggregate_operator_allowed else False,
            '{}:{}'.format(field.name, aggregate_operator) if aggregate_operator and aggregate_operator_allowed else field.name,
            field,
        )

    @api.model
    # groupby: list of tuples from get_group_by_tuple
    # Last groupby is the measurement aggregate
    def get_query_result(self, model, dom, measure_field, groupby=None, orderby=False):
        if groupby or measure_field and measure_field[0]:  # Not a simple count query (Use measure operator)
            if not measure_field or not measure_field[0]:
                # Set default measure to count
                measure_field = ('id', False, 'id')

            if groupby:
                groupby = list(filter(lambda g: g[0], groupby))  # Remove any empty groups
                fields = list(map(lambda g: g[0], groupby)) + [measure_field[2]]
                groups = list(map(lambda g: g[2], groupby))
            else:
                # No groupby with a measure field
                fields = [measure_field[2]]
                groups = []
            try:
                result = self.env[model.model].read_group(dom, fields=fields, groupby=groups, lazy=False, orderby=orderby)
            except Exception as ex:
                return False
            if not groups:
                # If the result is a simple result that parse out the final value
                result = result[0][measure_field[0]] if result else 0
        else:
            # Default to count operator
            result = self.env[model.model].search_count(dom)
        return result

    def action_open_data(self):
        if self.datasource not in ['query', 'python']:
            return super(DashboardDatasourceQuery, self).action_open_data()

        return self._action_open_data(
            self.query_1_config_model_id.model,
            action=self.action_id,
            domain=self.get_query_1_domain()
        )

    def get_query_config_date_range_x_label(self, type):
        if type == 'last_x_days':
            return "Number Of Days"
        elif type == 'last_x_months':
            return "Number Of Months"
        elif type == 'last_x_years':
            return "Number Of Years"
        else:
            return False

    @staticmethod
    def next_weekday(d, weekday):
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return d + timedelta(days_ahead)

    def previous_weekday(self, d, is_datetime, weekday):
        if is_datetime:
            # Datetime is in UTC, clear it so that we can convert to datetime in local TZ so we know what day it is
            # TODO: DST still has issues if the start/end range of a query is across the boundary of DST transition
            d_in_tz = fields.Datetime.context_timestamp(self, d.replace(tzinfo=None))
        else:
            d_in_tz = d

        days_ahead = weekday - d_in_tz.weekday()
        if days_ahead > 0:
            days_ahead -= 7
        target_d_in_tz = d_in_tz + timedelta(days_ahead)
        if is_datetime:
            return target_d_in_tz.astimezone(pytz.utc)
        else:
            return target_d_in_tz

    # Returns: start, end, is_datetime, error
    def get_date_range_values(self,
                              model,
                              field,
                              range_type,
                              custom_date_start, custom_date_end,
                              custom_datetime_start, custom_datetime_end,
                              current_goal_date_start, current_goal_date_end,
                              date_range_x,
                              config_date_start, config_date_end):
        if not model or not range_type or not field:
            return False, False, False, False

        try:
            is_datetime_field = isinstance(self.env[model.model]._fields[field.name], fields.Datetime)
            if is_datetime_field:
                now = datetime.now()
                # Strip timezone to allow correct handling of DST
                today = fields.Datetime.context_timestamp(self, now)\
                    .replace(hour=0, minute=0, second=0, microsecond=0)
                tz = today.tzinfo
                today = today.replace(tzinfo=None)
            else:
                today = fields.Date.context_today(self)
                if IS_ODOO_VERSION_BEFORE_v12:
                    today = fields.Date.from_string(today)

            if range_type == 'today':
                if is_datetime_field:
                    start = today
                    end = start + relativedelta(days=1)
                else:
                    start = today
                    end = False

            elif range_type == 'yesterday':
                start = today + relativedelta(days=-1)
                end = today

            elif range_type == 'this_week_monday_friday':
                target_day = 0  # Monday
                start = self.previous_weekday(today, is_datetime_field, target_day)
                end = start + relativedelta(days=5)

            elif range_type == 'this_week_monday_sunday':
                target_day = 0  # Monday
                start = self.previous_weekday(today, is_datetime_field, target_day)
                end = start + relativedelta(days=7)

            elif range_type == 'this_week_sunday_saturday':
                target_day = 6  # Sunday
                start = self.previous_weekday(today, is_datetime_field, target_day)
                end = start + relativedelta(days=7)


            elif range_type == 'this_month':
                start = today.replace(day=1)
                end = start + relativedelta(months=1)

            elif range_type == 'this_year':
                start = today.replace(day=1, month=1)
                end = start + relativedelta(years=1)

            elif range_type == 'custom':
                if is_datetime_field:
                    start = fields.Datetime.from_string(custom_datetime_start) if custom_datetime_start else False
                    end = fields.Datetime.from_string(custom_datetime_end) if custom_datetime_end else False
                else:
                    start = fields.Date.from_string(custom_date_start) if custom_date_start else False
                    end = fields.Date.from_string(custom_date_end) if custom_date_end else False
                    if end:
                        end = end + relativedelta(days=1)

            elif range_type == 'current_goal':
                start = fields.Date.from_string(current_goal_date_start) if current_goal_date_start else False
                end = fields.Date.from_string(current_goal_date_end) if current_goal_date_end else False

            elif range_type == 'last_x_days' and date_range_x:
                start = today - relativedelta(days=date_range_x)
                end = today

            elif range_type == 'last_x_months' and date_range_x:
                start = today - relativedelta(months=date_range_x)
                end = today

            elif range_type == 'last_x_years' and date_range_x:
                start = today - relativedelta(years=date_range_x)
                end = today

            elif range_type == 'last_month':
                last_month = today - relativedelta(months=1)
                start = last_month.replace(day=1)
                end = start + relativedelta(months=1)

            elif range_type == 'last_month_to_date':
                last_month = today - relativedelta(months=1)
                start = last_month.replace(day=1)
                end = last_month

            elif range_type == 'last_year':
                last_year = today - relativedelta(years=1)
                start = last_year.replace(day=1, month=1)
                end = start + relativedelta(years=1)

            elif range_type == 'last_year_to_date':
                last_year = today - relativedelta(years=1)
                start = last_year.replace(day=1, month=1)
                end = last_year

            # Allow a last effort default to use the linked config
            elif config_date_start or config_date_end:
                start = config_date_start if config_date_start else False
                end = config_date_end if config_date_end else False
                if end:
                    end = end + relativedelta(days=1)  # TODO: Is this needed?

            else:
                return False, False, is_datetime_field, False

            if is_datetime_field:
                # tz_name = self._context.get('tz') or self.env.user.tz
                # tz = pytz.timezone(tz_name)
                if start:
                    start = start.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
                if end:
                    end = end.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
            return start, end, is_datetime_field, False

        except Exception as ex:
            return False, False, False, "{}".format(ex)

    @staticmethod
    def get_working_days(start_date, end_date):
        if start_date and end_date:
            weekdays = rrule.rrule(rrule.DAILY, byweekday=range(0, 5), dtstart=start_date, until=end_date)
            weekdays = len(list(weekdays))
            # Remove current day if the current time is after 6pm
            # if int(time.strftime('%H')) >= 18:
            #     weekdays -= 1
            return float(weekdays)

    def _get_dom_eval_context(self):
        if IS_ODOO_VERSION_BEFORE_v12:
            context_today = lambda: fields.Date.from_string(fields.Date.context_today(self))
        else:
            context_today = lambda: fields.Date.context_today(self)
        return {
            'datetime': datetime,
            'date': date,
            'time': time,
            'relativedelta': relativedelta,
            'context_today': context_today,
            'record': self,
            'ref': self.env.ref,
            'uid': self.env.user.id,
            'user': self.env.user,
        }

    def _get_dom(self, dom_str, start_date, end_date, date_field):
        # TODO: This check is not needed anymore?
        if self.widget_type not in [
            'count',
            'count_over_total',
            'count_over_total_ratio',
            'count_over_total_ratio_percentage',
        ]:
            return []

        eval_context = self._get_dom_eval_context()
        dom = safe_eval(dom_str, eval_context) if dom_str else []

        if date_field:
            if start_date and end_date:
                dom.insert(0, (date_field.name, '>=', start_date))
                dom.insert(0, (date_field.name, '<', end_date))
            elif start_date:
                dom.insert(0, (date_field.name, '=', start_date))

        return dom

