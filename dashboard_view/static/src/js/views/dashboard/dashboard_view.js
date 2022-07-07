odoo.define('dashboard_view.DashboardView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var config = require('web.config');
var DashboardModel = require('dashboard_view.DashboardModel');
var DashboardRenderer = require('dashboard_view.DashboardRenderer');
var DashboardController = require('dashboard_view.DashboardController');
var pyUtils = require('web.py_utils');
var utils = require('web.utils');    
var fieldRegistry = require('web.field_registry');    

var _lt = core._lt;

var DashboardView = BasicView.extend({
    accesskey: "d",
    display_name: _lt("Dashboard"),
    icon: 'fa-tachometer',
    multi_record: true,
    searchable: true,
    groupable: false,
    enableTimeRangeMenu: 'true',
    jsLibs: [],    
    viewType: 'dashboard',
    
    config: _.extend({}, BasicView.prototype.config, {
        Model: DashboardModel,
        Renderer: DashboardRenderer,
        Controller: DashboardController
    }),

    /**
     * @constructor
     */
    
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.loadParams.type = 'record';
        this.aggregatesInfo = {}; // aggregates
        this.aggregatesInfo[this.viewType] = this.fieldsView.aggregatesInfo[this.viewType];
        this.loadParams.aggregatesInfo = this.aggregatesInfo;     
        this.formulasInfo = {}; // formulas
        this.formulasInfo[this.viewType] = this.fieldsView.formulasInfo[this.viewType];
        this.loadParams.formulasInfo = this.formulasInfo;
        this.viewsInfo = {}; // views
        this.viewsInfo[this.viewType] = this.fieldsView.viewsInfo[this.viewType];
        this.loadParams.viewsInfo = this.viewsInfo;        
        if (config.device.isMobile) {
            this.jsLibs.push('/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js');
        }
    },
    
    /**
     * Traverses the arch and calls '_processNode' on each of its nodes.
     *
     * @private
     * @param {Object} arch a parsed arch
     * @param {Object} fv the fieldsView Object, in which _processNode can
     *   access and add information (like the fields' attributes in the arch)
     */
    _processArch: function (arch, fv) {
        var self = this;
        fv.aggregatesInfo = Object.create(null); // aggregate
        fv.aggregatesInfo[fv.type] = Object.create(null);        
        fv.formulasInfo = Object.create(null); // formula
        fv.formulasInfo[fv.type] = Object.create(null);
        fv.viewsInfo = Object.create(null); // view
        fv.viewsInfo[fv.type] = Object.create(null);        
        utils.traverse(arch, function (node) {
            return self._processNode(node, fv);
        });
    },    
    
  /**
     * Processes a node of the arch (mainly nodes with tagname 'field'). Can
     * be overriden to handle other tagnames.
     *
     * @private
     * @param {Object} node
     * @param {Object} fv the fieldsView
     * @param {Object} fv.fieldsInfo
     * @param {Object} fv.fieldsInfo[viewType] fieldsInfo of the current viewType
     * @param {Object} fv.viewFields the result of a fields_get extend with the
     *   fields returned with the fields_view_get for the current viewType
     * @param {string} fv.viewType
     * @returns {boolean} false iff subnodes must not be visited.
     */
    _processNode: function (node, fv) {

        if (!_.isObject(node.attrs.modifiers)) {
            node.attrs.modifiers = node.attrs.modifiers ? JSON.parse(node.attrs.modifiers) : {};
        }
        
        if (node.tag === 'aggregate') {
            var viewType = fv.type;
            var aggregatesInfo = fv.aggregatesInfo[viewType];
            var fields = fv.viewFields;
            aggregatesInfo[node.attrs.name] = this._processField(viewType,
                fields[node.attrs.field], node.attrs ? _.clone(node.attrs) : {});
            return false;
        }
        
        if (node.tag === 'formula'){
            var viewType = fv.type;
            var formulasInfo = fv.formulasInfo[viewType];
            formulasInfo[node.attrs.name] = this._processFormula(viewType,
                node.attrs.name, node.attrs ? _.clone(node.attrs) : {});
            return false;
        }
        return node.tag !== 'arch';
    }, 
    
    /**
     * Processes a field node, in particular, put a flag on the field to give
     * special directives to the BasicModel.
     *
     * @private
     * @param {string} viewType
     * @param {Object} field - the field properties
     * @param {Object} attrs - the field attributes (from the xml)
     * @returns {Object} attrs
     */
    _processFormula: function (viewType, field, attrs) {
        var self = this;
        attrs.Widget = this._getFormulaWidgetClass(viewType, field, attrs);

        // process decoration attributes
        _.each(attrs, function (value, key) {
            var splitKey = key.split('-');
            if (splitKey[0] === 'decoration') {
                attrs.decorations = attrs.decorations || [];
                attrs.decorations.push({
                    className: 'text-' + splitKey[1],
                    expression: pyUtils._getPyJSAST(value),
                });
            }
        });

        if (!_.isObject(attrs.options)) { // parent arch could have already been processed (TODO this should not happen)
            attrs.options = attrs.options ? pyUtils.py_eval(attrs.options) : {};
        }

        // the relational data of invisible relational fields should not be
        // fetched (e.g. name_gets of invisible many2ones), at least those that
        // are always invisible.
        // the invisible attribute of a field is supposed to be static ("1" in
        // general), but not totally as it may use keys of the context
        // ("context.get('some_key')"). It is evaluated server-side, and the
        // result is put inside the modifiers as a value of the '(column_)invisible'
        // key, and the raw value is left in the invisible attribute (it is used
        // in debug mode for informational purposes).
        // this should change, for instance the server might set the evaluated
        // value in invisible, which could then be seen as static by the client,
        // and add another key in debug mode containing the raw value.
        // for now, we look inside the modifiers and consider the value only if
        // it is static (=== true),
        if (attrs.modifiers.invisible === true || attrs.modifiers.column_invisible === true) {
            attrs.__no_fetch = true;
        }
        return attrs;
    }, 
    
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the AbstractField specialization that should be used for the
     * given field informations. If there is no mentioned specific widget to
     * use, determines one according the field type.
     *
     * @private
     * @param {string} viewType
     * @param {Object} field
     * @param {Object} attrs
     * @returns {function|null} AbstractField specialization Class
     */
    _getFormulaWidgetClass: function (viewType, field, attrs) {
        var FieldWidget;
        if (attrs.widget) {
            FieldWidget = fieldRegistry.getAny([viewType + "." + attrs.widget, attrs.widget]);
            if (!FieldWidget) {
                console.warn("Missing widget: ", attrs.widget, " for field", attrs.name, "of type", "float");
            }
        }
        return FieldWidget || fieldRegistry.getAny([viewType + "." + "float", "float", "abstract"]);
    },    
    
    
});

return DashboardView;

});
