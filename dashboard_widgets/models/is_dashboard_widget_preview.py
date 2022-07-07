from odoo import models, fields, api


class DashboardWidget(models.Model):
    _inherit = 'is.dashboard.widget'  # Intentionally not abstract model

    preview_id = fields.Many2one('is.dashboard.widget.preview')
    preview_ids = fields.One2many('is.dashboard.widget.preview', string="Preview", compute="compute_preview")

    @api.depends(
        'name',
        'query_1_config_model_id',
        'widget_type',
        'color',
        'graph_type',
        'config_id',
        'kanban_class_main',
        'widget_hidden',
    )
    def compute_preview(self):
        # if self.env.context.get('preview_running'):
        #     return
        # return self._compute_preview

        try:
            self._cr.execute('SAVEPOINT record_dashboard_preview')

            for rec in self:
                skip_fields = [
                    'create_date',
                    '__last_update',
                    'create_uid',
                    'write_date',
                    'write_uid',
                    'preview_id'
                ]
                vals = {}
                ir_fields = self.env['ir.model.fields'].sudo().search_read(
                    fields=['name', 'ttype', 'compute', 'related', 'readonly', 'store'],
                    domain=[('model', '=', self._name)]
                )
                ir_fields = {f['name']: f for f in ir_fields}
                for field in self._fields:
                    if field in skip_fields:
                        continue

                    ir_field = ir_fields[field]
                    if ir_field['compute'] or ir_field['related'] or ir_field['readonly'] or not ir_field['store']:
                        continue

                    if ir_field['ttype'] in [
                        'char',
                        'float',
                        'integer',
                        'monetary',
                        'text',
                        'html',
                        'boolean',
                        'selection',
                        'date',
                        'datetime',
                    ]:
                        vals[field] = rec[field]

                    # TODO: m2o, m2m, 02m
                    if ir_field['ttype'] == "one2many":
                        pass

                    if ir_field['ttype'] == "many2one":
                        vals[field] = rec[field].id

                if not vals.get('name'):
                    vals['name'] = ""

                if not rec.preview_id:
                    rec.preview_id = self.env['is.dashboard.widget.preview'].sudo().create(vals)
                else:
                    rec.preview_id.sudo().write(vals)
                rec.preview_ids = rec.preview_id.ids
        except Exception:
            self._cr.execute('ROLLBACK TO SAVEPOINT record_dashboard_preview')
        else:
            self._cr.execute('RELEASE SAVEPOINT record_dashboard_preview')


class DashboardWidgetPreview(models.Model):
    _name = 'is.dashboard.widget.preview'
    _inherit = 'is.dashboard.widget.abstract'
    _description = "Dashboard Record Preview"
