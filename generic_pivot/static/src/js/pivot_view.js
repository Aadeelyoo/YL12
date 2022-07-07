odoo.define('generic_pivot.PivotView', function (require) {
"use strict";

var PivotView = require('web.PivotView');

PivotView.include({
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.controllerParams.adjustment = 'object';
        this.controllerParams.adjustName = 'adjust_pivot';
     },
});
});
