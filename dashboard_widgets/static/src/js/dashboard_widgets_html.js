odoo.define('dashboard_widgets_html', function(require) {

    // ODOO VERSION 10
//     var KanbanRecord = require('web_kanban.Record');

    // ODOO VERSION 11+
    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({
        start: function(){
            var self = this;
            var res = self._super();

            var $iframe = self.$el.find(".dashboard_widgets_html")
            if ($iframe[0] != undefined) {

                // define resize function
                var resize_iframe = function () {

                    // get dimensions of parent
                    var width = $iframe.closest('.dashboard_main').css('width');
                    var height = $iframe.closest('.dashboard_main').css('height');

                    // width is determined by the flexbox stuff and can be changed by updating the number of widgets on a line.
                    // a min height should be included for html widgets that are defined on their own line.
                    height = String(Math.max(parseInt(height), 300)) + "px";

                    // apply dimensions to iframe
                    $iframe.css('width', width);
                    $iframe.css('height', height);

                };

                // setup listeners
                $iframe.load(resize_iframe);
                $(window).resize(resize_iframe);
            }
            return res;
        },
    });
});
