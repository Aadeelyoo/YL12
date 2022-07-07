odoo.define('widget_chartjs', function (require) {
'use strict';

var IS_ODOO_VERSION_AFTER_v10 = true;
var IS_ODOO_VERSION_BEFORE_v12 = false;

// ODOO VERSION 10
//var Model = require('web.Model');
//var kanban_widgets = require('web_kanban.widgets');
//var AbstractField = kanban_widgets.AbstractField;

// ODOO VERSION 11+
var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');


var WidgetChartJS = AbstractField.extend({
    start: function() {
        if (IS_ODOO_VERSION_AFTER_v10){
            if (this.value){
                this.data = JSON.parse(this.value);
            }
        } else {
            if (this.field && this.field.raw_value) {
                this.data = JSON.parse(this.field.raw_value);
            }
        }
        if (!IS_ODOO_VERSION_AFTER_v10){
            this._render()
        }
        return this._super();
    },

    _render: function() {
        var self = this;
        self.$canvas = self.$el.append('<canvas>');
        self.$canvas = $(self.$canvas).find('canvas');  // TODO: What is the right way to not need to do this?

        var ctx = self.$canvas[0].getContext('2d');

        // show values on graph if show_values_on_graph is true
        var datalabels_display = (this.data && this.data['show_values_on_graph'] === true) ? true : false;
        // bar graphs handled the default anchor point poorly so move it to the top.
        var datalabels_anchor = (this.data && this.data['type'] == 'bar') ? 'end' : 'center';

        var data = _.extend({}, this.data, {
            options: {
                onClick: function(ev, el) {
                     ev.stopPropagation();

                     var activePoint = self.chart.getElementAtEvent(ev)[0];
                     if (! activePoint || !activePoint._chart){
                        return;
                     }
                     var data = activePoint._chart.data;
                     var datasetIndex = activePoint._datasetIndex;
                     var ds = data.datasets[datasetIndex]

                     var open_data = {
                         data_model: ds['model'],
                         data_action: ds['action_id'],
                         data_domain: ds['domains'][activePoint._index],
                     }

                     var call;
                     if (IS_ODOO_VERSION_AFTER_v10){
                         call = self._rpc({
                             model: self.model,
                             method: 'action_open_data_segment',
                             args: [[self.__parentedParent.id], open_data],
                         });
                     } else {
                        call = new Model(self.__parentedParent.model).call('action_open_data_segment', [[self.__parentedParent.id], open_data]);
                     }

                     call.done(function (action) {
                         if (action != undefined){
                             // need to add views if not defined
                             if (!('views' in action)) {
                                 action['views'] = [[false, 'list'], [false, 'form']];
                             }

                             var label = data['labels'][activePoint._index];
                             if (data.datasets.length > 1){
                                 var ds_label = ds['label'];
                                 action['name'] = ds_label + ": " + label;
                             } else {
                                 action['name'] = label;
                             }

                             // open the action
                             self.do_action(action, {'segment_selected': 1});
                         }
                     });
                 },
                plugins: {
                    colorschemes: {
                        scheme: 'brewer.Paired12'
                    },
                    datalabels: {
                        color: 'black',
                        display: function(context){
                            return datalabels_display && context.dataset.data[context.dataIndex];
                        },
                        anchor: datalabels_anchor,
                    },
                },
                emptyOverlay:{
                    fillStyle: 'rgba(255,255,255,0.5)',
                },
            },
        });

        if (IS_ODOO_VERSION_AFTER_v10) {
            self.$el.show();
        }

        self.chart = new Chart(ctx, data);
    },



    destroy: function(){
        this._super();
    },

});

if (IS_ODOO_VERSION_AFTER_v10){
    fieldRegistry.add('dashboard_graph_chart_js', WidgetChartJS);
} else {
    kanban_widgets.registry.add('dashboard_graph_chart_js', WidgetChartJS);
}

return WidgetChartJS;

});
