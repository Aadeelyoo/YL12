odoo.define('dashboard_view.DashboardModel', function (require) {
"use strict";

/**
 * The DashboardModel extends the BasicModel to add dashboard specific features...
 */

var BasicModel = require('web.BasicModel');
var pyUtils = require('web.py_utils');
var Domain = require('web.Domain');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var dataComparisonUtils = require('dashboard_view.dataComparisonUtils');
var computeVariation = dataComparisonUtils.computeVariation;
var _t = core._t;

var DashboardModel = BasicModel.extend({
    
    /**
     * @override
     */
    init: function () {
        this.default_group_operators = {'float': 'sum', 
                                        'integer': 'sum', 
                                        'monetary': 'sum', 
                                        'many2one': 'count_distinct'};
        this._super.apply(this, arguments);
    },    
    
    /**
     * The get method first argument is the handle returned by the load method.
     * It is optional (the handle can be undefined).  In some case, it makes
     * sense to use the handle as a key, for example the BasicModel holds the
     * data for various records, each with its local ID.
     *
     * synchronous method, it assumes that the resource has already been loaded.
     *
     * @param {string} id local id for the resource
     * @param {any} options
     * @param {boolean} [options.env=false] if true, will only  return res_id
     *   (if record) or res_ids (if list)
     * @param {boolean} [options.raw=false] if true, will not follow relations
     * @returns {Object}
     */
    get: function (id, options) {
        var result = this._super.apply(this, arguments);
        
        var self = this;

        if (!(id in this.localData)) {
            return null;
        }

        var element = this.localData[id];
        
        if (element.type === 'record') {
            result.aggregatesInfo = element.aggregatesInfo;
            result.formulasInfo = element.formulasInfo;
            result.viewsInfo = element.viewsInfo;            
            result.compare = element.compare;
            result.comparisonData = element.comparisonData;
            result.variation = element.variation;
            result.additionalMeasures = element.additionalMeasures;
            result.measure = element.measure;
        }
        
        return result;

    },
    
    /**
     * Turns a bag of properties into a valid local resource.  Also, register
     * the resource in the localData object.
     *
     * @param {Object} params
     * @param {Object} [params.aggregateValues={}]
     * @param {Object} [params.context={}] context of the action
     * @param {integer} [params.count=0] number of record being manipulated
     * @param {Object|Object[]} [params.data={}|[]] data of the record
     * @param {*[]} [params.domain=[]]
     * @param {Object} params.fields contains the description of each field
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Object[]} [params.fieldNames] the name of fields to load, the list
     *   of all fields by default
     * @param {string[]} [params.groupedBy=[]]
     * @param {boolean} [params.isOpen]
     * @param {integer} params.limit max number of records shown on screen (pager size)
     * @param {string} params.modelName
     * @param {integer} [params.offset]
     * @param {boolean} [params.openGroupByDefault]
     * @param {Object[]} [params.orderedBy=[]]
     * @param {integer[]} [params.orderedResIDs]
     * @param {string} [params.parentID] model name ID of the parent model
     * @param {Object} [params.rawContext]
     * @param {[type]} [params.ref]
     * @param {string} [params.relationField]
     * @param {integer|null} [params.res_id] actual id of record in the server
     * @param {integer[]} [params.res_ids] context in which the data point is used, from a list of res_id
     * @param {boolean} [params.static=false]
     * @param {string} [params.type='record'|'list']
     * @param {[type]} [params.value]
     * @param {string} [params.viewType] the type of the view, e.g. 'list' or 'form'
     * @returns {Object} the resource created
     */
    _makeDataPoint: function (params) {
        
        var type = params.type || ('domain' in params && 'list') || 'record';
        var res_id, value;
        var res_ids = params.res_ids || [];
        var data = params.data || (type === 'record' ? {} : []);
        var comparisonData = params.comparisonData || (type === 'record' ? {} : []);
        var variation = params.variation || (type === 'record' ? {} : []);        
        if (type === 'record') {
            res_id = params.res_id || (params.data && params.data.id);
            if (res_id) {
                data.id = res_id;
            } else {
                res_id = _.uniqueId('virtual_');
            }
        } else {
            var isValueArray = params.value instanceof Array;
            res_id = isValueArray ? params.value[0] : undefined;
            value = isValueArray ? params.value[1] : params.value;
        }

        var fields = _.extend({
            display_name: {type: 'char'},
            id: {type: 'integer'},
        }, params.fields);

        var dataPoint = {
            _cache: type === 'list' ? {} : undefined,
            _changes: null,
            _domains: {},
            _rawChanges: {},
            aggregateValues: params.aggregateValues || {},
            context: params.context,
            count: params.count || res_ids.length,
            data: data,
            domain: params.domain || [],
            fields: fields,
            fieldsInfo: params.fieldsInfo,
            groupedBy: params.groupedBy || [],
            id: _.uniqueId(params.modelName + '_'),
            isOpen: params.isOpen,
            limit: type === 'record' ? 1 : params.limit,
            loadMoreOffset: 0,
            model: params.modelName,
            offset: params.offset || (type === 'record' ? _.indexOf(res_ids, res_id) : 0),
            openGroupByDefault: params.openGroupByDefault,
            orderedBy: params.orderedBy || [],
            orderedResIDs: params.orderedResIDs,
            parentID: params.parentID,
            rawContext: params.rawContext,
            ref: params.ref || res_id,
            relationField: params.relationField,
            res_id: res_id,
            res_ids: res_ids,
            specialData: {},
            _specialDataCache: {},
            static: params.static || false,
            type: type,  // 'record' | 'list'
            value: value,
            viewType: params.viewType,
            aggregatesInfo: params.aggregatesInfo, 
            formulasInfo: params.formulasInfo,
            viewsInfo: params.viewsInfo,             
            compare: params.compare, 
            comparisonTimeRange: params.comparisonTimeRange, 
            timeRange: params.timeRange,
            comparisonData: comparisonData,
            variation: variation,
            additionalMeasures: params.additionalMeasures || []
        };

        if (params.measure) {
            dataPoint.measure = params.measure;
        }

        // _editionViewType is a dict whose keys are field names and which is populated when a field
        // is edited with the viewType as value. This is useful for one2manys to determine whether
        // or not a field is readonly (using the readonly modifiers of the view in which the field
        // has been edited)
        dataPoint._editionViewType = {};

        dataPoint.evalModifiers = this._evalModifiers.bind(this, dataPoint);
        dataPoint.getContext = this._getContext.bind(this, dataPoint);
        dataPoint.getDomain = this._getDomain.bind(this, dataPoint);
        dataPoint.getFieldNames = this._getFieldNames.bind(this, dataPoint);
        dataPoint.isDirty = this.isDirty.bind(this, dataPoint.id);

        this.localData[dataPoint.id] = dataPoint;

        return dataPoint;
    },

    /**
     * Main entry point, the goal of this method is to fetch and process all
     * data (following relations if necessary) for a given record/list.
     *
     * @todo document all params
     *
     * @param {any} params
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Object} params.fields contains the description of each field
     * @param {string} [params.type] 'record' or 'list'
     * @param {string} [params.recordID] an ID for an existing resource.
     * @returns {Deferred<string>} resolves to a local id, or handle
     */
    load: function (params) {
        // FIXME: the following seems only to be used by the basic_model_tests
        // so it should probably be removed and the tests should be adapted
        params.viewType = params.viewType || 'default';
        if (!params.aggregatesInfo) {
            params.aggregatesInfo = {};
            params.aggregatesInfo[params.viewType] = {};
        }
        
        if (!params.additionalMeasures) {
            params.additionalMeasures = params.aggregatesInfo && params.aggregatesInfo[params.viewType] ? _.map(params.aggregatesInfo[params.viewType], 'field') : [];
        }

        if (!params.formulasInfo) {
            params.formulasInfo = {};            
            params.formulasInfo[params.viewType] = {};
        }
        
        if (!params.viewsInfo) {
            params.viewsInfo = {};
            params.viewsInfo[params.viewType] = {};
        }        
        
        var dataPoint = this._makeDataPoint(params);
    
        return this._load(dataPoint).then(function () {
            return dataPoint.id;
        });        
    },
    
    /**
     * Reload all data for a given resource
     *
     * @private
     * @param {string} id local id for a resource
     * @param {Object} [options]
     * @param {boolean} [options.keepChanges=false] if true, doesn't discard the
     *   changes on the record before reloading it
     * @returns {Deferred<string>} resolves to the id of the resource
     */
    _reload: function (id, options) {
        var self = this;
        options = options || {};
        
        var element = this.localData[id];

        if (options.context !== undefined) {
            element.context = options.context;
            var timeRangeMenuData = options.context.timeRangeMenuData;
            if (timeRangeMenuData) {
                element.timeRange = timeRangeMenuData.timeRange || [];
                element.comparisonTimeRange = timeRangeMenuData.comparisonTimeRange || [];
                element.compare = element.comparisonTimeRange.length > 0;
            } else {
                element.timeRange = [];
                element.comparisonTimeRange = [];
                element.compare = false;
                element = _.omit(element, 'comparisonData');
                element = _.omit(element, 'variation');
            }
        }
        
        if (options.domain !== undefined) {
            element.domain = options.domain;
        }
        if (options.groupBy !== undefined) {
            element.groupedBy = options.groupBy;
        }
        if (options.limit !== undefined) {
            element.limit = options.limit;
        }
        if (options.offset !== undefined) {
            this._setOffset(element.id, options.offset);
        }
        if (options.loadMoreOffset !== undefined) {
            element.loadMoreOffset = options.loadMoreOffset;
        } else {
            // reset if not specified
            element.loadMoreOffset = 0;
        }
        if (options.currentId !== undefined) {
            element.res_id = options.currentId;
        }
        if (options.ids !== undefined) {
            element.res_ids = options.ids;
            element.count = element.res_ids.length;
        }
        if (element.type === 'record') {
            element.offset = _.indexOf(element.res_ids, element.res_id);
        }
        
        return this._load(element).then(function () {
            self.localData[element.id] = element;
            return element.id;
        });
    },
    
    /**
     * Returns the list of field names of the given element according to its
     * default view type.
     *
     * @param {Object} element an element from the localData
     * @param {Object} [options]
     * @param {Object} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {string[]} the list of field names
     */
    _getFieldNames: function (element, options) {
        var aggregatesInfo = element.aggregatesInfo;    
        var viewType = options && options.viewType || element.viewType;
        return Object.keys(aggregatesInfo && aggregatesInfo[viewType] || {});
    },        
    
    /**
     * For a given resource of type 'record', fetch all data.
     *
     * @param {Object} record local resource
     * @param {Object} [options]
     * @param {string[]} [options.fieldNames] the list of fields to fetch. If
     *   not given, fetch all the fields in record.fieldNames (+ display_name)
     * @param {string} [optinos.viewType] the type of view for which the record
     *   is fetched (usefull to load the adequate fields), by defaults, uses
     *   record.viewType
     * @returns {Deferred<Object>} resolves to the record or is rejected in
     *   case no id given were valid ids
     */ 
    _fetchRecord: function (record, options) {
        options = options || {};
        var self = this;
        var session = this.getSession();     
        var fieldNames = options.fieldNames || record.getFieldNames(options);
        return $.when.apply($, _.map(fieldNames, function (fieldName) {
            var aggregateInfo = record.aggregatesInfo[record.viewType][fieldName] || {};            
            var domain = record.domain.concat(Domain.prototype.stringToArray(aggregateInfo.domain || '[]'));
            var field = record.fields[aggregateInfo.field];
            var fspec = aggregateInfo.name + ':' + (aggregateInfo.group_operator || field.group_operator || self.default_group_operators[field.type]) + '(' + aggregateInfo.field + ')';
            var defs = [];
            
            if (record.model === 'stock.report' && (aggregateInfo.field === 'stock_value' || aggregateInfo.field === 'valuation')) {
                if (aggregateInfo.field === 'stock_value') {
                    defs.push(self._rpc({
                            model: record.model,
                            method: 'compute_stock_value',
                            args: [aggregateInfo.group_operator || field.group_operator || self.default_group_operators[field.type]]
                        }).then (function (value){
                        var result = {};
                        result[aggregateInfo.name] = value;
                        if (result[aggregateInfo.name] === null) {
                            result[aggregateInfo.name] = 0;
                        }
                        record.data = _.extend({}, record.data, result);
                        }));
                } 
                
                if (aggregateInfo.field === 'valuation') {
                    defs.push(self._rpc({
                            model: record.model,
                            method: 'compute_valuation',
                            args: [domain.concat(record.timeRange), aggregateInfo.group_operator || field.group_operator || self.default_group_operators[field.type]]
                        }).then (function (value){
                        var result = {};
                        result[aggregateInfo.name] = value;
                        if (result[aggregateInfo.name] === null) {
                            result[aggregateInfo.name] = 0;
                        }
                        record.data = _.extend({}, record.data, result);
                        }));
                }
            } else {
                defs.push(self._rpc({
                        model: record.model,
                        method: 'read_group',
                        fields: [fspec],
                        domain: domain.concat(record.timeRange),                
                        context: _.extend({}, record.getContext(), {bin_size: true}),
                    }).then (function (result){
                        result = _.pick(result[0], aggregateInfo.name);
                        if (result[aggregateInfo.name] === null) {
                            result[aggregateInfo.name] = 0;
                        }
                        record.data = _.extend({}, record.data, result);
                    }));
            }
            if (record.compare) {
                if (record.model === 'stock.report' && (aggregateInfo.field === 'stock_value' || aggregateInfo.field === 'valuation')) {
                    if (aggregateInfo.field === 'stock_value') {
                        defs.push(self._rpc({
                            model: record.model,
                            method: 'compute_stock_value'
                        }).then (function (value){
                            var result={}, variation = {};
                            result[aggregateInfo.name] = value;
                            if (result[aggregateInfo.name] === null) {
                                result[aggregateInfo.name] = 0;
                            }
                            record.comparisonData = _.extend({}, record.comparisonData, result);
                            variation[aggregateInfo.name] = computeVariation(record.data[aggregateInfo.name], record.comparisonData[aggregateInfo.name]);
                            record.variation = _.extend({}, record.variation, variation);
                        }));
                    } 
                
                    if (aggregateInfo.field === 'valuation') {
                        defs.push(self._rpc({
                            model: record.model,
                            method: 'compute_valuation',
                            args: [domain.concat(record.comparisonTimeRange)]
                        }).then (function (value){
                            var result={}, variation = {};
                            result[aggregateInfo.name] = value;
                            if (result[aggregateInfo.name] === null) {
                                result[aggregateInfo.name] = 0;
                            }
                            record.comparisonData = _.extend({}, record.comparisonData, result);
                            variation[aggregateInfo.name] = computeVariation(record.data[aggregateInfo.name], record.comparisonData[aggregateInfo.name]);
                            record.variation = _.extend({}, record.variation, variation);
                        }));
                    }
                } else {
                    defs.push(self._rpc({
                        model: record.model,
                        method: 'read_group',
                        fields: [fspec],
                        domain: domain.concat(record.comparisonTimeRange),                
                        context: _.extend({}, record.getContext(), {bin_size: true}),
                    }).then (function (result){
                        var variation = {};
                        result = _.pick(result[0], aggregateInfo.name);
                        if (result[aggregateInfo.name] === null) {
                            result[aggregateInfo.name] = 0;
                        }
                        record.comparisonData = _.extend({}, record.comparisonData, result);
                        variation[aggregateInfo.name] = computeVariation(record.data[aggregateInfo.name], record.comparisonData[aggregateInfo.name]);
                        record.variation = _.extend({}, record.variation, variation);
                    }));
                }
            }
            return $.when.apply($, defs);
        }))
        .then (function (){
            _.map(record.formulasInfo[record.viewType], function (formulaInfo) {
                var result = {};
                try {
                    result[formulaInfo.name] = 0;
                    result[formulaInfo.name] = pyUtils.py_eval(formulaInfo.value, {'record': record.data});
                    record.data = _.extend({}, record.data, result);
                } catch (e) {record.data = _.extend({}, record.data, result);}
                if (record.compare){
                    try {
                        result[formulaInfo.name] = 0;
                        result[formulaInfo.name] = pyUtils.py_eval(formulaInfo.value, {'record': record.comparisonData});
                        record.comparisonData = _.extend({}, record.comparisonData, result);
                    } 
                    catch (e) {record.comparisonData = _.extend({}, record.comparisonData, result);}
                    finally {
                        var variation = {};
                        variation[formulaInfo.name] = computeVariation(record.data[formulaInfo.name], record.comparisonData[formulaInfo.name]);
                        record.variation = _.extend({}, record.variation, variation);
                    }
                }
            });
        })
        .then (function (){
            return self._rpc({
                    model: 'res.company',
                    method: 'read',
                    args: [[session.company_id], ['currency_id']],
                    context: _.extend({}, record.getContext(), {bin_size: true}),                
                })
                .then (function (result){
                    var currency_id = result[0]['currency_id'][0];
                    return self._rpc({
                        model: 'res.currency',
                        method: 'read',
                        args: [[currency_id], ['decimal_places']],
                        context: _.extend({}, record.getContext(), {bin_size: true}),                
                    })
                    .then (function (result){
                        session.user_currency = _.extend({}, session.user_currency, result[0]);
                    });
                });
        });
    },    
    

});
    
return DashboardModel;

});
