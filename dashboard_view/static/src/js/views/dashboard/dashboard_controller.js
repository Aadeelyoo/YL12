odoo.define('dashboard_view.DashboardController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var Domain = require('web.Domain');    
    
var DashboardController = BasicController.extend({
    
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        aggregateToggle: '_onAggregateToggle',
        viewFullscreen: '_onViewFullscreen' 
    }),
    
    _onViewFullscreen: function (event) {
        var state = this.model.get(this.handle);
        var context = _.extend({}, state.context, state.viewsInfo[state.viewType][event.data.view_id].getContext());
        
        this.do_action({
            name: _.str.capitalize(event.data.view_type) + ' ' + 'Analysis',
            type: 'ir.actions.act_window',
            res_model: this.modelName,
            views: [[event.data.view_id || false, event.data.view_type]],
            target: 'current',
            context: context,
        }, {'keepSearchView': true});
    },

    _onAggregateToggle: function (event) {
        var filterNames = [];        
        var domain_name = event.data.domain_name;
        var domain = event.data.domain;
        var domain_label = event.data.domain_label;
        var measure = event.data.measure;
        
        event.data = [];
        
        if (measure){
            this.model.localData[this.handle].measure = measure;
        }
        
        this.searchView.query.each(function (facet) {
            facet.get('values').forEach(function (value) {
                if (value.value) {
                    filterNames.push(value.value.attrs.name);
                }
            });
        });
        
        if (domain && !_.contains(filterNames, domain_name)){
            var data = [];
            var groupId = _.uniqueId('__group__');
            var filterName = _.uniqueId('__filter__');

            var filter = {
                attrs: {
                    domain: Domain.prototype.arrayToString(domain),
                    string: domain_label,
                    name: domain_name
                },
                children: [],
                tag: 'filter',
            }

            data.push({
                itemId: filterName,
                groupId: groupId,
                filter: filter,
            });

            event.data = data;
        }

        this.searchView._onNewFilters(event);
        
    },
    
    
    /**
     * @constructor
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
    },
    
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getTitle: function () {
        return this.displayName;
    },


});

return DashboardController;

});
