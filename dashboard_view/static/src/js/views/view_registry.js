odoo.define('dashboard_view.viewRegistry', function (require) {
"use strict";

var DashboardView = require('dashboard_view.DashboardView');

var viewRegistry = require('web.view_registry');

viewRegistry.add('dashboard', DashboardView);

});