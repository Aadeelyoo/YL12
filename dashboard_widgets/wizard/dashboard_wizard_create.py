from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval as safe_eval

from datetime import datetime, date, time, timedelta


class DashboardWizardCreate(models.TransientModel):
    _name = 'is.dashboard.widget.wizard.create'
    _description = 'Dashboard Create Wizard'

    dashboard_title = fields.Char(string="Dashboard Title", required=True)
    menu_name = fields.Char(string="Menu Name")
    menu_id = fields.Many2one("ir.ui.menu", string="Parent Menu")

    tag_id = fields.Many2one('is.dashboard.widget.tag', string="Dashboard Tag")
    domain = fields.Char(string="Domain", default="[['tag_ids','=','']]")
    domain_model = fields.Char(default='is.dashboard.widget')

    manual_context = fields.Text(string="Context", help="Add default context values to make new dashboard items show on this dashboard", default="{}")

    auto_generate_default_context = fields.Boolean(default=True, string="Auto generate defaults")
    default_context = fields.Text(compute="compute_default_context")
    context = fields.Text(string="Action Context", compute="compute_default_context")

    def action_create(self):
        self.ensure_one()

        domain = False
        if self.tag_id:
            domain = "[('tag_ids', 'in', [{}])]".format(self.tag_id.id)
        else:
            domain = self.domain or []
        action = self.env['ir.actions.act_window'].create({
            'name': self.dashboard_title,
            'type': 'ir.actions.act_window',
            'res_model': 'is.dashboard.widget',
            'view_type': 'form',
            'view_mode': 'kanban,tree,form',
            'domain': domain,
            'context': self.context or {},
            'help': 'Create your first dashboard item',
        })

        menu = self.env['ir.ui.menu'].sudo().create({
            'name': self.menu_name,
            'action': 'ir.actions.act_window,' + str(action.id),
            'parent_id': self.menu_id.id,
        })

        return action.read()[0]

    @api.onchange('dashboard_title')
    def onchange_dashboard_title(self):
        for rec in self:
            rec.menu_name = rec.dashboard_title

    @api.onchange('domain', 'manual_context', 'tag_id')
    def compute_default_context(self):
        for rec in self:
            eval_context = self._get_dom_eval_context()
            if rec.auto_generate_default_context:
                default_context = {}
                if rec.tag_id:
                    default_context['default_tag_ids'] = [rec.tag_id.id]
                else:
                    dom = safe_eval(self.domain, eval_context) if self.domain else []

                    for dom_line in dom:
                        if len(dom_line) != 3:
                            continue

                        if dom_line[0] in ['id']:
                            continue  # Skip lines that can not be defaults

                        if '.' not in dom_line[0] and dom_line[0] in self.env['is.dashboard.widget']._fields:
                            if dom_line[1] == '=':
                                field = self.env['is.dashboard.widget']._fields[dom_line[0]]
                                if field.type == 'many2many' and 'name' in self.env[field.comodel_name]._fields:
                                    val = dom_line[2]
                                    result = self.env[field.comodel_name].search([('name', '=', dom_line[2])], limit=1)
                                    if result:
                                        val = [result.id]
                                    if val:
                                        default_context['default_' + dom_line[0]] = val
                            if dom_line[1] in ['<=', '>=', 'ilike', 'in']:
                                val = dom_line[2]
                                if val:
                                    default_context['default_' + dom_line[0]] = val

                rec.default_context = default_context
                manual_context = safe_eval(rec.manual_context, eval_context) if self.manual_context else {}
                default_context.update(manual_context)
                self.context = default_context
            else:
                self.context = rec.manual_context

    def _get_dom_eval_context(self):
        return {
            'datetime': datetime,
            'date': date,
            'time': time,
            'context_today': lambda: fields.Date.context_today(self),
            'record': self,
            'ref': self.env.ref,
        }
