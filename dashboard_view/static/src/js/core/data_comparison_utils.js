odoo.define('dashboard_view.dataComparisonUtils', function (require) {
"use strict";

var fieldUtils = require('web.field_utils');

/**
 * @param {Number} value
 * @param {Number} comparisonValue
 * @returns {Object}
 */
function computeVariation (value, comparisonValue) {
    var magnitude;
    var signClass;
    var fontClass;

    if (!isNaN(value) && !isNaN(comparisonValue)) {
        if (comparisonValue === 0) {
            if (value === 0) {
                magnitude = 0;
            } else if (value > 0){
                magnitude = 1;
            } else {
                magnitude = -1;
            }
        } else {
            magnitude = (value - comparisonValue) / Math.abs(comparisonValue);
        }
        if (magnitude > 0) {
            signClass = ' o_positive';
            fontClass = ' fa fa-caret-up';
        } else if (magnitude < 0) {
            signClass = ' o_negative';
            fontClass = ' fa fa-caret-down';
        } else if (magnitude === 0) {
            signClass = ' o_null';
            fontClass = NaN;
        }
        return {magnitude: magnitude, signClass: signClass, fontClass: fontClass};
	} else {
		return {magnitude: NaN};
	}
}

return {
	computeVariation: computeVariation
};

});
