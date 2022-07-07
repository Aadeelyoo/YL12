odoo.define('dashboard_view.DashboardRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var viewRegistry = require('web.view_registry');
var dom = require('web.dom');
var Domain = require('web.Domain');
var core = require('web.core');
var session = require('web.session');
var config = require('web.config');
var fieldUtils = require('web.field_utils');
var QWeb = core.qweb;
    
var DashboardRenderer = BasicRenderer.extend({
    className: "o_dashboard",
    
    events: _.extend({}, BasicRenderer.prototype.events, {
        'click .aggregate-toggle': '_onAggregateToggle',
        'mouseover .aggregate-toggle': '_onMouseOver',
        'mouseout .aggregate-toggle': '_onMouseOut',
        'click .btn-fullscreen': '_doFullScreen',        
    }),    
    
    // default col attributes for the rendering of groups
    INNER_GROUP_COL: 6,
    OUTER_GROUP_COL: 6,
    
    _doFullScreen: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var $target = $(event.currentTarget);
        this.trigger_up('viewFullscreen', {'view_id': parseInt($target.attr('view_id')), 'view_type': $target.attr('view_type')});
    },
    
    _onMouseOver: function (event) {
        var $target = $(event.currentTarget);
        $target.find('.o_search').show();
    },
    
    _onMouseOut: function (event) {
        var $target = $(event.currentTarget); 
        $target.find('.o_search').hide();
    },
    
    _onAggregateToggle: function (event) {
        var self = this;
        event.preventDefault();
        event.stopPropagation();
        var $target = $(event.currentTarget);
        _.each(this.allFieldWidgets[this.state.id], function (widget) {
            if (widget.__node.attrs.name === $target.data('name')) {            
                self.trigger_up('aggregateToggle', {'domain_name': widget.__node.attrs.name, 'domain': widget.__node.attrs.domain, 'domain_label': widget.__node.attrs.domain_label || widget.__node.attrs.name, 'measure': widget.__node.attrs.measure || widget.__node.attrs.field});
            }
        });
    },
    
    /**
     * @constructor
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
    },
    
/**
     * Main entry point for the rendering.  From here, we call _renderNode on
     * the root of the arch, then, when every deferred (from the field widgets)
     * are done, it will resolves itself.
     *
     * @private
     * @override method from BasicRenderer
     * @returns {Deferred}
     */
    _renderView: function () {
        var self = this;

        // render the dashboard and evaluate the modifiers
        var defs = [];
        this.defs = defs;
        var $dashboard = this._renderNode(this.arch).addClass(this.className);
        delete this.defs;

        return $.when.apply($, defs).then(function () {
            self._updateView($dashboard.contents());
        }, function () {
            $dashboard.remove();
        });
    },
    
/**
     * Updates the dashboard's $el with new content.
     *
     * @private
     * @see _renderView
     * @param {JQuery} $newContent
     */
    _updateView: function ($newContent) {
        var self = this;
        
        // Set the new content of the dashboard view, and toggle classnames
        this.$el.html($newContent);
        
        // Attach the tooltips on the fields' label
        _.each(this.allFieldWidgets[this.state.id], function (widget) {
            if (config.debug || widget.attrs.help) {
                self._addFieldTooltip(widget, []);
            }
        });
    },
    
    /**
     * Render a node, from the arch of the view. It is a generic method, that
     * will dispatch on specific other methods.  The rendering of a node is a
     * jQuery element (or a string), with the correct classes, attrs, and
     * content.
     *
     * For fields, it will return the $el of the field widget. Note that this
     * method is synchronous, field widgets are instantiated and appended, but
     * if they are asynchronous, they register their deferred in this.defs, and
     * the _renderView method will properly wait.
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement | string}
     */
    _renderNode: function (node) {
        var renderer = this['_renderTag' + _.str.capitalize(node.tag)];
        if (renderer) {
            return renderer.call(this, node);
        }
        
        if (_.isString(node)) {
            return node;
        }
    },    
    
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagDashboard: function (node) {
        var $result = $('<div/>');
        if (node.attrs.class) {
            $result.addClass(node.attrs.class);
        }
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagGroup: function (node) {
        var isOuterGroup = _.some(node.children, function (child) {
            return child.tag === 'group';
        });
        if (!isOuterGroup) {
            return this._renderInnerGroup(node);
        }
        return this._renderOuterGroup(node);
    },
    
    /**
     * Renders a 'group' node, which contains 'group' nodes in its children.
     *
     * @param {Object} node]
     * @returns {JQueryElement}
     */
    _renderOuterGroup: function (node) {
        var self = this;
        var $result = $('<div/>', {class: 'o_group'});
        var nbCols = parseInt(node.attrs.col, 10) || this.OUTER_GROUP_COL;
        var colSize = Math.max(1, Math.round(12 / nbCols));
        if (node.attrs.string) {
            var $sep = $('<div/>', {class: 'o_horizontal_separator'}).text(node.attrs.string);
            $result.append($sep);
        }
        $result.append(_.map(node.children, function (child) {
            if (child.tag === 'newline') {
                return $('<br/>');
            }
            var $child = self._renderNode(child);
            $child.addClass('o_group_col_' + (colSize * (parseInt(child.attrs.colspan, 10) || 1)));
            return $child;
        }));
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroup: function (node) {
        var self = this;
        var $result = $('<div/>');        
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);

        var nbCols = parseInt(node.attrs.col, 10) || this.INNER_GROUP_COL;
        var colSize = Math.max(1, Math.round(12 / nbCols));

        if (node.attrs.string) {
            var $sep = $('<div class="o_horizontal_separator">' + node.attrs.string + '</div>');
            $result.append($sep);
        }

        var rows = [];
        var $currentRow = $result;
        var currentColspan = 0;
        _.each(node.children, function (child) {
            if (child.tag === 'newline') {
                rows.push($currentRow);
                $currentRow = $('<div/>');
                currentColspan = 0;
                return;
            }

            var colspan = parseInt(child.attrs.colspan, 10)|| 1;
            var finalColspan = colspan;            
            currentColspan += colspan;
            
            var $divs = $('<div/>', {class: 'o_inner_group_col_' + colSize}).append(self._renderNode(child));
            $currentRow.append($divs);
        });
        rows.push($currentRow);

        _.each(rows, function ($div) {
            _.each($div.children(':not(.o_horizontal_separator)'), function (el) {
                var $el = $(el);
                _.each($el.children(), function (child) {
                    var $child = $(child);
                    
                    if ($child.hasClass('o_dashboard_aggregate') || $child.hasClass('o_dashboard_formula')){
                        if ($child.hasClass('o_invisible_modifier')) {
                            $el.hide();
                        }
                    }

                    if ($child.hasClass('o_dashboard_widget')){
                        if ($child.hasClass('o_dashboard_pie_chart')) {
                            $el.addClass('o_piecharts_group_col_' + colSize);
                        }
                    }                    
                });
            });
            $result.append($div);
        });

        return $result;
    },    
    
    getViewInfoAndParams: function(viewType, modifiers, fieldsViews){
        var self = this;              
        var fieldsView = fieldsViews[viewType];
        var domain = self.state.domain.concat(
            Domain.prototype.stringToArray(modifiers.domain || '[]'));        
        var viewParams = {
            context: self.state.context,
            domain: domain,
            groupBy: [],
            isEmbedded: true,
            modelName: fieldsView.model,
            viewID: fieldsView.view_id
        };

        var viewInfo = {
            arch: fieldsView.arch,
            fields: fieldsView.fields,
            viewFields: fieldsView.viewFields
        };
        
        return {'viewInfo': viewInfo, 'viewParams': viewParams};
    },
    
    loadView: function(viewType, viewInfo){
        var fn = this['_load' + _.str.capitalize(viewType)];
        if (fn) {
            return fn.call(this, viewInfo);
        }
    },
    
    _loadGraph: function(viewInfo){
        var self = this;
        var fragment = document.createDocumentFragment();
        var currentController = this.state.viewsInfo[this.viewType][viewInfo.viewParams.viewID];
        if (currentController) {    
            viewInfo.viewParams.context = _.extend({}, viewInfo.viewParams.context, currentController.getContext());
        }

        var View = viewRegistry.get('graph');
        if (this.state.measure){
            viewInfo.viewParams.context = _.extend({}, viewInfo.viewParams.context, {'graph_measure': this.state.measure});
        }
        viewInfo.viewParams.additionalMeasures = this.state.additionalMeasures;
        var view = new View(viewInfo.viewInfo, viewInfo.viewParams);
        return view.getController(self).then(function (controller) {
                self.controller = controller;
                self.state.viewsInfo[self.viewType][viewInfo.viewParams.viewID] = controller;
                return self.controller.appendTo(fragment);
        }).then(function () {
            return fragment;
        });
    },
    
    _loadPivot: function(viewInfo){
        var self = this;
        var fragment = document.createDocumentFragment();
        var currentController = this.state.viewsInfo[this.viewType][viewInfo.viewParams.viewID];
        if (currentController) {
            viewInfo.viewParams.context = _.extend({}, viewInfo.viewParams.context, currentController.getContext());
        }
        var View = viewRegistry.get('pivot');
        if (this.state.measure){
            viewInfo.viewParams.context = _.extend({}, viewInfo.viewParams.context, {'pivot_measures': [this.state.measure]});
        }
        viewInfo.viewParams.additionalMeasures = this.state.additionalMeasures;
        var view = new View(viewInfo.viewInfo, viewInfo.viewParams);
        return view.getController(self).then(function (controller) {
                self.controller = controller;
                self.state.viewsInfo[self.viewType][viewInfo.viewParams.viewID] = controller;
                return self.controller.appendTo(fragment);
        }).then(function () {
            return fragment;
        });
    },
    
    _loadCalendar: function(viewInfo){
        var self = this;
        var fragment = document.createDocumentFragment();
        var currentController = this.state.viewsInfo[this.viewType][viewInfo.viewParams.viewID];
        if (currentController) {
            viewInfo.viewParams.context = _.extend({}, viewInfo.viewParams.context, currentController.getContext());
        }
        var View = viewRegistry.get('calendar');
        var view = new View(viewInfo.viewInfo, viewInfo.viewParams);
        return view.getController(self).then(function (controller) {
                self.controller = controller;
                self.state.viewsInfo[self.viewType][viewInfo.viewParams.viewID] = controller;
                return self.controller.appendTo(fragment);
        }).then(function () {
            return fragment;
        });
    },    
    
    loadPieChart: function(attrs, viewInfo){
        var self = this;
        var fragment = document.createDocumentFragment();
        
        var arch = QWeb.render('web.PieChart', {
            modifiers: attrs.modifiers,
            title: attrs.title || attrs.modifiers.title || attrs.modifiers.measure
        });
        var View = viewRegistry.get('graph');
        
        viewInfo.viewParams['withControlPanel'] = false;
        viewInfo.viewParams['isEmbedded'] = true;
        viewInfo.viewParams['mode'] = 'pie';
        viewInfo.viewInfo['arch'] = arch;
        viewInfo.viewParams.context = _.omit(viewInfo.viewParams.context, 'graph_groupbys', 'graph_intervalMapping', 'graph_measure', 'graph_mode');
        
        var view = new View(viewInfo.viewInfo, viewInfo.viewParams);
        this.widgets.push(view);
        return view.getController(self).then(function (controller) {
                self.controller = controller;
                self.state.viewsInfo[self.viewType][viewInfo.viewParams.viewID] = controller;                
                return self.controller.appendTo(fragment);
        }).then(function () {
                return fragment;
        });
    },
    
     _renderTagView: function (node) {
        var self = this;
        var $el = $('<div class="o_dashboard_view"/>');
         
        this._rpc({
                model: 'ir.ui.view',
                method: 'ref_to_view_id',
                args: [node.attrs.ref || null]
        }).then(function (view_id) {
                self.loadViews(self.state.model, self.state.context, [[view_id || null, node.attrs.type]], [])
                .then(self.getViewInfoAndParams.bind(self, node.attrs.type, node.attrs.modifiers))
                .then(self.loadView.bind(self, node.attrs.type))
                .then(function (fragment){
                    var $buttons = $('<div>');
                    self.controller.renderButtons($buttons);
                    if ($buttons.children().length) {
                        $el.append($buttons.contents());
                    }
                    $el.append("<div aria-label='Full Screen' class='btn btn-secondary btn-fullscreen fa fa-arrows-alt' title='' data-original-title='Full Screen' view_id=" + view_id + " view_type=" + node.attrs.type + "></div>");
                    
                    dom.append($el, fragment, {
                        callbacks: [{widget: self.controller}],
                        in_DOM: true,
                    });
                });
            });
        return $el;
    },
    
    _renderTagWidget: function (node) {
        var self = this;
        var context = _.omit(this.state.context, 'graph_groupbys', 'graph_intervalMapping', 'graph_measure', 'graph_mode');
        var $el = $('<div class="o_dashboard_widget"/>');
        if (node.attrs.name === 'pie_chart'){
            $el.addClass('o_dashboard_pie_chart');
            self.loadViews(self.state.model, context, [[null, 'graph']], [])
            .then(self.getViewInfoAndParams.bind(self, 'graph', node.attrs.modifiers))
            .then(self.loadPieChart.bind(self, node.attrs))
            .then(function (fragment){
                dom.append($el, fragment, {
                    callbacks: [{widget: self.controller}],
                    in_DOM: true,
                });
            });
        } else {
            return this._renderWidget(this.state, node);
        }
        return $el;
    },
    
    _renderTagAggregate: function (node) {
        return this._renderAggregateWidget(node, this.state);
    },
    
    _renderTagFormula: function(node){
        return this._renderFormulaWidget(node, this.state);
    },
    
    _renderAggregateWidget: function (node, record, options) {
        
        function evalClickable(mod) {
            if (mod === undefined || mod === '0' || mod === 'false' || mod === 'False') {
                return false;
            }
            return true;
        }
        
        function getWidget(value){    
            // Initialize and register the widget
            var Widget = record.aggregatesInfo[self.viewType][aggregateName].Widget;
            var widget = new Widget(self, node.attrs.field, record, {
                'viewType': self.viewType, 
                'attrs': {
                    'widget': node.attrs.widget ? node.attrs.widget : record.fields[node.attrs.field].type === 'many2one' ? 'integer' : false,
                    'help': node.attrs.help, 
                    'options': { 
                        'currency_id': session.user_currency.id, 
                        'decimals': session.user_currency.decimal_places, 
                        'humanReadable': function (val) {return val >= 1000 ? true : false;},
                        'formatterCallback': function (val) {return val;}
                        }
                    }
            });

            if (!widget.value){widget.value = value}; // Set value
            widget.appendTo($("<div/>"));
            return widget;
        }        
        
        options = options || {};
        var self = this;
        var $widget = $(QWeb.render('dashboard_view.aggregate', {'widget': node.attrs, 'clickable': 'clickable' in node.attrs ? evalClickable(node.attrs.clickable) : true, 'compare': record.compare}));
        var aggregateName = node.attrs.name;
        var field = record.fields[node.attrs.field];
        var modifiers = this._registerModifiers(node, record, null, options);
        var session = this.getSession();
       
        if (modifiers.invisible){
            $widget.addClass("o_invisible_modifier");
        }
        
        var widget = getWidget(record.data[aggregateName]);
        widget.__node = node; // TODO get rid of this if possible one day
        var formattedValue = widget._formatValue(record.data[aggregateName]);
        var valueLabel = node.attrs.value_label;
                
        if (record.compare) {
            var comparisonWidget = getWidget(record.comparisonData[aggregateName]);
            var formattedComparisonValue = comparisonWidget._formatValue(record.comparisonData[aggregateName]);
            formattedValue = '<strong>' + formattedValue + '</strong><span> vs </span><strong>' + formattedComparisonValue + '</strong>';
            valueLabel = valueLabel ? '<strong>' + valueLabel + '</strong>' : valueLabel;
            widget.$el.find('.o_progressbar_value').addClass('o_text_bold');
            comparisonWidget.$el.find('.o_progressbar_value').addClass('o_text_bold');
            widget.$el = widget.$el.add("<span> vs </span>").add(comparisonWidget.$el);
            $widget.find(".o_value").addClass(record.variation[aggregateName].signClass).html("<span class='o_caret " + record.variation[aggregateName].fontClass + "'/> " + fieldUtils.format.percentage(record.variation[aggregateName].magnitude, field));
            $widget.find('.o_variation').html(node.attrs.widget === 'progressbar' ? widget.$el : formattedValue ? formattedValue + ' ' + (valueLabel || '') : '-');            
            $widget.find(".o_search").addClass(record.variation[aggregateName].signClass);
        } else {
            $widget.find('.o_value').html(node.attrs.widget === 'progressbar' ? widget.$el : formattedValue ? formattedValue + ' ' + (valueLabel || '') : '-');
        }

        // Register the widget so that it can easily be found again
        if (self.allFieldWidgets[record.id] === undefined) {
            self.allFieldWidgets[record.id] = [];
        }

        widget.__node = node; // TODO get rid of this if possible one day
        
        $widget.find(".o_label").html(node.attrs.string || field.string || formulaName);
        $widget.find('.o_search').hide();
        widget.$el = $widget;
        self.allFieldWidgets[record.id].push(widget);
        return $widget;
    },
    
    _renderFormulaWidget: function (node, record, options) {
        
        function getWidget(value) {
            // Initialize and register the widget
            var Widget = record.formulasInfo[self.viewType][formulaName].Widget;

            var widget = new Widget(self, formulaName, record, {
                'viewType': self.viewType, 
                'attrs': {
                    'widget': node.attrs.widget,
                    'help': node.attrs.help, 
                    'options': { 
                        'currency_id': session.user_currency.id, 
                        'decimals': session.user_currency.decimal_places, 
                        'humanReadable': function (val) {return val >= 1000 ? true : false;},
                        'formatterCallback': function (val) {return val;}
                        }
                    }
            });

            if (!widget.value){widget.value = value}; // Set value
            widget.appendTo($("<div/>"));
            return widget;
        }
        
        options = options || {};
        var self = this;
        var $widget = $(QWeb.render('dashboard_view.formula', {'compare': record.compare}));
        var formulaName = node.attrs.name;
        var field = {};
        field[formulaName] = {'type': 'float', 
                              'string': node.attrs.string || formulaName};         
        var modifiers = this._registerModifiers(node, record, null, options);
        var session = this.getSession();
        var record = _.clone(record);
        record.fields = _.extend({}, record.fields, field);        
       
        if (modifiers.invisible){
            $widget.addClass("o_invisible_modifier");
        }
    
        // Register the widget so that it can easily be found again
        if (self.allFieldWidgets[record.id] === undefined) {
            self.allFieldWidgets[record.id] = [];
        }
        
        var widget = getWidget(record.data[formulaName]);        
        widget.__node = node; // TODO get rid of this if possible one day
        var formattedValue = widget._formatValue(record.data[formulaName]);
        var valueLabel = node.attrs.value_label;

        if (record.compare) {
            var comparisonWidget = getWidget(record.comparisonData[formulaName]);
            var formattedComparisonValue = comparisonWidget._formatValue(record.comparisonData[formulaName]);
            formattedValue = '<strong>' + formattedValue + '</strong><span> vs </span><strong>' + formattedComparisonValue + '</strong>';
            valueLabel = valueLabel ? '<strong>' + valueLabel + '</strong>' : valueLabel;
            widget.$el.find('.o_progressbar_value').addClass('o_text_bold');
            comparisonWidget.$el.find('.o_progressbar_value').addClass('o_text_bold');            
            widget.$el = widget.$el.add("<span> vs </span>").add(comparisonWidget.$el);
            $widget.find(".o_value").addClass(record.variation[formulaName].signClass).html("<span class='o_caret " + record.variation[formulaName].fontClass + "'/> " + fieldUtils.format.percentage(record.variation[formulaName].magnitude, field));
            $widget.find('.o_variation').html(node.attrs.widget === 'progressbar' ? widget.$el : formattedValue ? formattedValue + ' ' + (valueLabel || '') : '-');
        } else {
            $widget.find('.o_value').html(node.attrs.widget === 'progressbar' ? widget.$el : formattedValue ? formattedValue + ' ' + (valueLabel || '') : '-');
        }
        
        $widget.find(".o_label").html(field[formulaName].string);
        widget.$el = $widget;
        self.allFieldWidgets[record.id].push(widget);
        return $widget;
    },
    
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a tooltip on a $node, depending on a field description
     *
     * @param {FieldWidget} widget
     * @param {$node} $node
     */
    _addFieldTooltip: function (widget, $node) {
        // optional argument $node, the jQuery element on which the tooltip
        // should be attached if not given, the tooltip is attached on the
        // widget's $el
        $node = $node.length ? $node : widget.$el;

        $node.tooltip({
            title: function () {
                return QWeb.render('Widget.tooltip', {
                    debug: config.debug,
                    widget: widget,
                });
            }
        });
    },    

});

return DashboardRenderer;

});
