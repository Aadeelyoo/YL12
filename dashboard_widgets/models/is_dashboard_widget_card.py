from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as safe_eval

from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import rrule

IS_ODOO_VERSION_BEFORE_v12 = False


class DashboardWidget(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    locked = fields.Boolean(default=False, help="Allow editing of this records configuration", copy=False)

    display_mode = fields.Selection(default='card', selection_add=[
        ('card', 'KPI Card'),
    ])

    # TODO: To remove in a future version
    widget_type = fields.Selection(default='count', selection=[
        ("count", "Count"),
        ("count_over_total", "Count/Total"),
        ("count_over_total_ratio", "Count/Total Ratio"),
        ("count_over_total_ratio_percentage", "Count/Total Ratio (Percentage)"),
    ])

    # TODO: To replace above field in a future version
    # card_1_show_query_value = fields.Boolean()
    # card_1_show_query_forecast = fields.Boolean()
    # card_1_show_query_goal = fields.Boolean()

    card_hide_when_no_data = fields.Boolean()

    card_1_goal_standard = fields.Float(string="Standard Goal")


    card_1_config_enable_forecast = fields.Boolean()


    # error = fields.Text(string="Error", compute="_compute_count")
    # card_2_config_domain = fields.Char(oldname='total_domain', default='[]')



    widget_type_is_a_count = fields.Boolean(string="Technical field to show count fields", compute='_compute_widget_type_is_a_count', store=True)
    widget_type_is_a_count_over_total = fields.Boolean(string="Technical field to show count over total fields", compute='_compute_widget_type_is_a_count', store=True)

    # aggregate_field = fields.Char(string="Aggregate Field", help="Field to use to aggregate domain results. If empty will default to count")
    # aggregate_field_id = fields.Many2one('ir.model.fields', string="Aggregate Field", help="Field to use to aggregate domain results. If empty will default to count")

    # count_domain = fields.Text("Domain for count type widgets", default='[]')
    # total_domain = fields.Text("Domain for count total type widgets", default='[]')
    # use_domain_widget = fields.Boolean(default=True)
    # count_domain_widget_domain = fields.Text(compute="compute_domain_widget", inverse="inverse_domain_widget")  # Used for domain widget to allow this feature to be turned on/off
    # total_domain_widget_domain = fields.Text(compute="compute_domain_widget", inverse="inverse_domain_widget")  # Used for domain widget to allow this feature to be turned on/off

    count = fields.Float(string="Value Raw", compute="_compute_count")
    count_cache = fields.Float(string="Value Raw (Cached)")
    count_display = fields.Char("Value", compute='_compute_count_display')

    total = fields.Float(string="Value (Total) Raw", compute="_compute_count")
    total_cache = fields.Float(string="Value (Total) (Cached)")
    total_display = fields.Char("Value (Total)", compute='_compute_total_display')

    # error = fields.Text(string="Error", compute="_compute_count")
    # has_goal = fields.Boolean(string="Enable Goals", default=False)



    goal_count_variance = fields.Float(compute="compute_goal_variance", string="Goal Variance Raw")
    goal_count_variance_display = fields.Char("Goal Variance", compute='_compute_goal_count_variance_display')

    goal_total_variance = fields.Float(compute="compute_goal_variance", string="Goal Variance (2) Raw")
    goal_total_variance_display = fields.Char("Goal Variance (2)", compute='_compute_goal_total_variance_display')

    goal_forecast_count_variance = fields.Float(compute="compute_goal_variance", string="Forecasted Variance (1) Raw")
    goal_forecast_total_variance = fields.Float(compute="compute_goal_variance", string="Forecasted Variance (2) Raw")


    current_goal_count = fields.Float(string="Current Goal (1) Raw", compute="compute_current_goal_count")
    current_goal_count_display = fields.Char("Current Goal (1)", compute='_compute_current_goal_count_display')

    current_goal_total = fields.Float(string="Current Goal (2) Raw", compute="compute_current_goal_total")
    current_goal_total_display = fields.Char("Current Goal (2)", compute='_compute_current_goal_total_display')

    forecast_count = fields.Float(string="Forecast Raw", compute="compute_forecast")
    forecast_count_display = fields.Char("Forecast", compute='_compute_forecast_count_display')

    expected_count = fields.Float(string="Forecast Raw", compute="compute_forecast")
    expected_count_display = fields.Char("Forecast", compute='_compute_expected_count_display')

    expected_total = fields.Float(string="Forecast (2) Raw", compute="compute_forecast")
    expected_total_display = fields.Char("Forecast (2)", compute='_compute_expected_total_display')

    forecast_total = fields.Float(string="Forecast (2) Raw", compute="compute_forecast")
    forecast_total_display = fields.Char("Forecast (2)", compute='_compute_forecast_total_display')

    goal_forecast_count_variance_display = fields.Char(string="Forecasted Variation (1)", compute="_compute_goal_forecast_count_variance_display")
    goal_forecast_total_variance_display = fields.Char(string="Forecasted Variation (2)", compute="_compute_goal_forecast_total_variance_display")

    forecast_count_meets_goal = fields.Boolean(compute="compute_forecast")
    forecast_total_meets_goal = fields.Boolean(compute="compute_forecast")
    has_forecast_1 = fields.Boolean(string="Has Forecast (1)", compute="compute_forecast")
    has_forecast_2 = fields.Boolean(string="Has Forecast (2)", compute="compute_forecast")

    show_expected_1 = fields.Boolean(string="Show Expected (1)", default=False)
    show_goal_1 = fields.Boolean(string="Show Goal (1)", default=True)
    show_expected_1_label = fields.Char(string="Label: Expected (1)", default="Expected: ")
    show_goal_1_label = fields.Char(string="Label: Goal (1)", default="Goal: ")
    show_expected_2 = fields.Boolean(string="Show Expected (2)", default=False)
    show_goal_2 = fields.Boolean(string="Show Goal (2)", default=False)
    show_expected_2_label = fields.Char(string="Label: Expected (2)", default="Expected (2): ")
    show_goal_2_label = fields.Char(string="Label: Goal (2)", default="Goal (2): ")

    show_forecast_1 = fields.Boolean(string="Show Forecast (1)", default=True)
    show_forecast_1_label = fields.Char(string="Label: Forecast (1)", default="Forecast: ")
    show_forecast_2 = fields.Boolean(string="Show Forecast (2)", default=False)
    show_forecast_2_label = fields.Char(string="Label: Forecast (2)", default="Forecast (2): ")

    show_variation_1 = fields.Boolean(string="Show Variation (1)", default=True)
    show_variation_1_label = fields.Char(string="Label: Variation (1)", default="Variation: ")
    show_variation_2 = fields.Boolean(string="Show Variation (2)", default=False)
    show_variation_2_label = fields.Char(string="Label: Variation (2)", default="Variation (2): ")

    show_forecasted_variation_1 = fields.Boolean(string="Show Forecasted Variation (1)", default=True)
    show_forecasted_variation_1_label = fields.Char(string="Label: Forecasted Variation (1)", default="Forecasted Variation: ")
    show_forecasted_variation_2 = fields.Boolean(string="Show Forecasted Variation (2)", default=False)
    show_forecasted_variation_2_label = fields.Char(string="Label: Forecasted Variation (2)", default="Forecasted Variation (2): ")

    # auto_filter_date_range = fields.Selection(selection=[
    #     ('today', 'Today'),
    #     ('this_month', 'This Month'),
    #     ('this_year', 'This Year'),
    #     ('last_x_days', 'Last X Days'),
    #     ('last_x_months', 'Last X Months'),
    #     ('last_x_years', 'Last X Years'),
    #     ('custom', 'Custom'),
    #     ('current_goal', 'Current Goal'),
    # ])
    # custom_date_start = fields.Date(string="Custom Start")
    # custom_date_end = fields.Date(string="Custom End")



    # auto_filter_date_range_x = fields.Integer(default=1)
    # auto_filter_date_range_x_label = fields.Char(compute="compute_auto_filter_date_range_x_type")



    # @api.onchange('aggregate_field_id')
    # def onchange_aggregate_field_id(self):
    #     for rec in self:
    #         rec.aggregate_field = rec.aggregate_field_id.name

    # @api.depends('query_1_config_domain', 'total_domain', 'use_domain_widget')
    # def compute_domain_widget(self):
    #     for rec in self:
    #         rec.count_domain_widget_domain = rec.count_domain if rec.use_domain_widget else []
    #         rec.total_domain_widget_domain = rec.total_domain if rec.use_domain_widget else []

    # # Make sure we have the latest domain from the widget if it is enabled
    # @api.onchange('count_domain_widget_domain', 'total_domain_widget_domain')
    # def inverse_domain_widget(self):
    #     for rec in self:
    #         rec.count_domain = rec.count_domain_widget_domain if rec.use_domain_widget else rec.count_domain
    #         rec.total_domain = rec.total_domain_widget_domain if rec.use_domain_widget else rec.total_domain



    def _format_field(self, field_for_type, value):
        try:
            force_type = 'float' if self.widget_type in ['count_over_total_ratio', 'count_over_total_ratio_percentage'] else False
            percent = self.widget_type in ['count_over_total_ratio_percentage']

            t = force_type or field_for_type.ttype or 'integer'
            if t in ['integer', 'float', 'monetary']:
                if t == 'monetary':
                    # todo get a better way of doing this, ideally, get the first result and use the currency field defined on the field_for_value and read the value
                    currency = self.env.user.currency_id
                else:
                    currency = False

                if currency:
                    dp = currency.decimal_places
                elif t == 'integer' or field_for_type and self.env[field_for_type.model]._fields[field_for_type.name].group_operator == 'count':
                    dp = 0
                else:
                    dp = 2  # todo, should this be configurable, based on the field and the rounding rules?

                fmt = "%.{0}f".format(dp)
                lang = self.env['res.lang']._lang_get(self.env.lang)
                formatted_amount = lang.format(fmt, value, True, t == 'monetary')

                if t == 'monetary':
                    formatted_amount = ('{symbol}{value}' if currency.position == 'before' else '{value}{symbol}').format(
                        symbol=currency.symbol or '',
                        value=formatted_amount
                    )

                if percent:
                    formatted_amount = '{}%'.format(formatted_amount)
                return formatted_amount
            else:
                return '{}'.format(value)
        except Exception as ex:
            return 'ERROR: {}'.format(ex)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'count')
    def _compute_count_display(self):
        for rec in self:
            try:
                rec.count_display = rec._format_field(rec.query_1_config_measure_field_id, rec.count)
            except:
                rec.count_display = 'ERROR'

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'total')
    def _compute_total_display(self):
        for rec in self:
            rec.total_display = rec._format_field(rec.query_2_config_measure_field_id, rec.total)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'current_goal_count')
    def _compute_current_goal_count_display(self):
        for rec in self:
            rec.current_goal_count_display = rec._format_field(rec.query_1_config_measure_field_id, rec.current_goal_count)

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'current_goal_total')
    def _compute_current_goal_total_display(self):
        for rec in self:
            rec.current_goal_total_display = rec._format_field(rec.query_2_config_measure_field_id, rec.current_goal_total)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'goal_count_variance')
    def _compute_goal_count_variance_display(self):
        for rec in self:
            rec.goal_count_variance_display = rec._format_field(rec.query_1_config_measure_field_id, rec.goal_count_variance)

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'goal_total_variance')
    def _compute_goal_total_variance_display(self):
        for rec in self:
            rec.goal_total_variance_display = rec._format_field(rec.query_2_config_measure_field_id, rec.goal_total_variance)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'forecast_count')
    def _compute_forecast_count_display(self):
        for rec in self:
            rec.forecast_count_display = rec._format_field(rec.query_1_config_measure_field_id, rec.forecast_count)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'expected_count')
    def _compute_expected_count_display(self):
        for rec in self:
            rec.expected_count_display = rec._format_field(rec.query_1_config_measure_field_id, rec.expected_count)

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'forecast_total')
    def _compute_forecast_total_display(self):
        for rec in self:
            rec.forecast_total_display = rec._format_field(rec.query_2_config_measure_field_id, rec.forecast_total)

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'expected_total')
    def _compute_expected_total_display(self):
        for rec in self:
            rec.expected_total_display = rec._format_field(rec.query_2_config_measure_field_id, rec.expected_total)

    @api.depends('query_1_config_measure_field_id', 'widget_type', 'forecast_total')
    def _compute_goal_forecast_count_variance_display(self):
        for rec in self:
            try:
                rec.goal_forecast_count_variance_display = rec._format_field(rec.query_1_config_measure_field_id, rec.goal_forecast_count_variance)
            except:
                rec.goal_forecast_count_variance_display = 'ERROR'

    @api.depends('query_2_config_measure_field_id', 'widget_type', 'forecast_total')
    def _compute_goal_forecast_total_variance_display(self):
        for rec in self:
            rec.goal_forecast_total_variance_display = rec._format_field(rec.query_2_config_measure_field_id, rec.goal_forecast_total_variance)

    @api.depends('widget_type')
    def _compute_widget_type_is_a_count(self):
        for rec in self:
            rec.widget_type_is_a_count = rec.widget_type and rec.widget_type.startswith('count')
            rec.widget_type_is_a_count_over_total = rec.widget_type and rec.widget_type.startswith('count_over_total')

    @api.depends('count', 'total', 'current_goal_count', 'current_goal_total', 'forecast_count', 'forecast_total')
    def compute_goal_variance(self):
        for rec in self:
            rec.goal_count_variance = (rec.count - rec.current_goal_count) if rec.current_goal_count else 0
            rec.goal_total_variance = (rec.total - rec.current_goal_total) if rec.current_goal_total else 0

            rec.goal_forecast_count_variance = (rec.forecast_count - rec.current_goal_count) if rec.current_goal_count else 0
            rec.goal_forecast_total_variance = (rec.forecast_total - rec.current_goal_total) if rec.current_goal_total else 0

    def _compute_forecast(self, date_range_start, date_range_end, datetime_range_start, datetime_range_end):
        is_datetime = True if datetime_range_start or datetime_range_end else False

        start_date = date_range_start or datetime_range_start
        end_date = date_range_end or datetime_range_end

        if IS_ODOO_VERSION_BEFORE_v12:
            if is_datetime:
                start_date = fields.Datetime.from_string(start_date)
                end_date = fields.Datetime.from_string(end_date)
            else:
                start_date = fields.Date.from_string(start_date)
                end_date = fields.Date.from_string(end_date)

        has_forecast = start_date and end_date

        today = date.today()
        business_days_done = self.get_working_days(start_date, today)
        business_days_total = self.get_working_days(start_date, end_date)
        business_days_percent = business_days_done / business_days_total if business_days_total else 0

        return has_forecast, business_days_percent

    def compute_forecast(self):
        for rec in self:
            rec.has_forecast_1, business_days_percent_1 = self._compute_forecast(
                rec.query_1_config_date_range_start,
                rec.query_1_config_date_range_end,
                rec.query_1_config_datetime_range_start,
                rec.query_1_config_datetime_range_end,
            )

            rec.has_forecast_2, business_days_percent_2 = self._compute_forecast(
                rec.query_2_config_date_range_start,
                rec.query_2_config_date_range_end,
                rec.query_2_config_datetime_range_start,
                rec.query_2_config_datetime_range_end,
            )

            rec.forecast_count = rec.count / business_days_percent_1 if business_days_percent_1 else 0
            rec.forecast_total = rec.total / business_days_percent_2 if business_days_percent_2 else 0
            rec.expected_count = rec.current_goal_count * business_days_percent_1 if business_days_percent_1 else 0
            rec.expected_total = rec.current_goal_total * business_days_percent_2 if business_days_percent_2 else 0

    kanban_class_count = fields.Char(string="Kanban Class Count", compute='_compute_kanban_class_count')
    kanban_class_name = fields.Char(string="Kanban Class Name", compute='_compute_kanban_class_count')
    kanban_class_expected = fields.Char(string="Kanban Class Expected", compute='_compute_kanban_class_count')
    kanban_class_goal = fields.Char(string="Kanban Class Goal", compute='_compute_kanban_class_count')
    kanban_class_variation = fields.Char(string="Kanban Class Variation", compute='_compute_kanban_class_count')
    kanban_class_forecast = fields.Char(string="Kanban Class Forecast", compute='_compute_kanban_class_count')
    kanban_class_forecasted_variation = fields.Char(string="Kanban Class Forecast", compute='_compute_kanban_class_count')

    @api.depends('goal_1_is_greater_than', 'forecast_count', 'current_goal_total', 'count')
    def _compute_kanban_class_count(self):
        for rec in self:
            rec.kanban_class_name = ''
            rec.kanban_class_goal = ''

            if rec.query_1_config_enable_goal:
                if rec.goal_1_is_greater_than:
                    forecast_met = rec.forecast_count >= rec.current_goal_count
                    count_met = rec.count >= rec.current_goal_count
                else:
                    forecast_met = rec.forecast_count <= rec.current_goal_count
                    count_met = rec.count <= rec.current_goal_count

                if rec.has_forecast_1:
                    rec.kanban_class_variation = 'variation-met' if forecast_met else 'variation-not-met'
                    rec.kanban_class_count = ''
                    rec.kanban_class_forecast = 'forecast-met' if forecast_met else 'forecast-not-met'
                    rec.kanban_class_forecasted_variation = 'forecasted-variation-met' if forecast_met else 'forecasted-variation-not-met'
                else:
                    rec.kanban_class_variation = ''
                    rec.kanban_class_count = 'count-met' if count_met else 'count-not-met'
                    rec.kanban_class_forecast = ''
                    rec.kanban_class_forecasted_variation = ''
            else:
                rec.kanban_class_variation = ''
                rec.kanban_class_count = ''
                rec.kanban_class_forecast = ''
                rec.kanban_class_forecasted_variation = ''

            rec.kanban_class_expected = ''  # TODO: Add class if needed

    def cron_update_cache(self):
        self.search([('use_cache', '=', True)]).action_update_cache()

    def action_update_cache(self):
        for rec in self:
            if rec.use_cache:
                rec.with_context(update_dashboard_cache=True)._compute_count()

    def _update_cache(self):
        can_write = self.check_access_rights('write', raise_exception=False)

        for rec in self:
            if rec.use_cache and can_write:
                rec.count_cache = rec.count
                rec.total_cache = rec.total
                rec.last_cache_updated_datetime = datetime.now()

    @api.depends(
        # 'query_1_domain',
        # 'query_2_domain',
        'query_1_config_measure_field_id',
        'query_1_config_date_range_field_id',
        'query_1_config_date_range_type', 'query_1_config_date_range_x',
        'query_1_config_model_id', 'query_2_config_model_id',
        'widget_type',
        'config_id.config_date_start',
        'config_id.config_date_end',
        'current_goal_date_start',
        'current_goal_date_end',
        'query_1_config_date_range_custom_start',
        'query_1_config_date_range_custom_end',
        'query_1_config_datetime_range_custom_start',
        'query_1_config_datetime_range_custom_end',

    )
    def _compute_count(self):
        can_write = self.check_access_rights('write', raise_exception=False)
        for rec in self:
            if rec.use_cache and not self.env.context.get('update_dashboard_cache', False):
                rec.count = rec.count_cache
                rec.total = rec.total_cache
                continue

            if rec.datasource == 'python':
                rec.run_python_count()
                rec._update_cache()
                continue

            if can_write:
                rec.query_1_error = False,
                rec.query_1_error_date = False,
                rec.query_2_error = False,
                rec.query_2_error_date = False,

            try:
                if not rec.query_1_config_model_id:
                    rec.count = 0
                    rec.total = 0
                    rec._update_cache()
                    continue
                if rec.widget_type not in ['count', 'count_over_total', 'count_over_total_ratio', 'count_over_total_ratio_percentage']:
                    rec.count = 0
                    rec.total = 0
                    rec._update_cache()
                    continue

                count = 0
                if rec.query_1_config_model_id:
                    count = self.get_query_result(
                        rec.query_1_config_model_id,
                        rec.get_query_1_domain(),
                        rec.get_group_by_tuple(rec.query_1_config_measure_field_id, rec.query_1_config_measure_operator, date_only_aggregate=False),
                    )

                total = 0
                if rec.query_2_config_model_id:
                    total = self.get_query_result(
                        rec.query_2_config_model_id,
                        rec.get_query_2_domain(),
                        rec.get_group_by_tuple(rec.query_2_config_measure_field_id, rec.query_2_config_measure_operator, date_only_aggregate=False),
                    )

                if rec.widget_type == 'count_over_total_ratio':
                    rec.count = float(count) / total if total else 0
                    rec.total = 0
                elif rec.widget_type == 'count_over_total_ratio_percentage':
                    rec.count = float(count) / total * 100 if total else 0
                    rec.total = 0
                else:
                    rec.count = count
                    rec.total = total

                rec._update_cache()

                if hasattr(rec, 'compute_preview'):
                    rec.compute_preview()
            except Exception as ex:
                rec.count = 0
                rec.total = 0
                rec._update_cache()
                if can_write:
                    rec.query_1_error = "{}".format(ex)

    def get_widget_hidden(self):
        if self.card_hide_when_no_data:
            return not self.count and not self.total
        else:
            return super(DashboardWidget, self).get_widget_hidden()


class DashboardWidgetGoal(models.Model):
    _name = 'is.dashboard.widget.goal'
    _description = "Dashboard Goal Line"
    _rec_name = 'date'
    _order = 'date'

    date = fields.Date("Start Date", required=True)
    goal = fields.Float(string="Goal Value", oldname='goal_count')
    dashboard_widget_1_id = fields.Many2one(string="Dashboard Item", comodel_name='is.dashboard.widget', oldname='dashboard_widget_id')
    dashboard_widget_2_id = fields.Many2one(string="Dashboard Item", comodel_name='is.dashboard.widget')
    dashboard_widget_id_type = fields.Selection(string='Type', compute='_compute_dashboard_widget_id_type', selection=lambda self: self.env['is.dashboard.widget.abstract']._fields['widget_type'].selection)

    @api.depends('dashboard_widget_1_id.widget_type', 'dashboard_widget_2_id.widget_type')
    def _compute_dashboard_widget_id_type(self):
        for rec in self:
            widget = rec.dashboard_widget_1_id or rec.dashboard_widget_2_id
            rec.dashboard_widget_id_type = widget.widget_type
