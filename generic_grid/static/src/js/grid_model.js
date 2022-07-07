odoo.define('generic_grid.GridModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var concurrency = require('web.concurrency');

return AbstractModel.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._gridValue = null;
        this._getMutex = new concurrency.Mutex();
        this._getPending = null;
        this._waitingDef = $.Deferred();
    },

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return this._gridValue;
    },
    /**
     * @override
     * @param {Object} context
     * @returns {Object}
     */
    getContext: function (context) {
        var c = _.extend({}, this.context, context);
        return c;
    },
    /**
     * The data from the grid view basically come from a read_group so we don't
     * have any res_ids. A big domain is thus computed with the domain of all
     * cells and this big domain is used to search for res_ids.
     */
    getResIds: function () {
        var data = this._gridValue;
        if (!_.isArray(data)) {
            data = [data];
        }

        var domain = [];
        // count number of non-empty cells and only add those to the search
        var cells = 0;

        for (var i = 0; i < data.length; i++) {
            var grid = data[i].grid;

            for (var j = 0; j < grid.length; j++) {
                var row = grid[j];
                for (var k = 0; k < row.length; k++) {
                    var cell = row[k];
                    if (cell.size !== 0) {
                        cells++;
                        domain.push.apply(domain, cell.domain);
                    }
                }
            }
        }

        // if there are no elements in the grid we'll get an empty domain
        // which will select all records of the model... that is *not* what
        // we want
        if (cells === 0) {
            return $.when([]);
        }

        while (--cells > 0) {
            domain.unshift('|');
        }

        return this._rpc({
            model: this.modelName,
            method: 'search',
            args: [domain],
            context: this.getContext(),
        });
    },
    /**
     * @override
     * @param {Object} params
     * @returns {Deferred}
     */
    load: function (params) {
        this.modelName = params.modelName;
        this.rowFields = params.rowFields;
        this.sectionField = params.sectionField;
        this.colField = params.colField;
        this.cellField = params.cellField;
        this.ranges = params.ranges;
        this.currentRange = params.currentRange;
        this.domain = params.domain;
        this.context = params.context;
        var groupedBy = (params.groupedBy && params.groupedBy.length) ? params.groupedBy : this.rowFields;
        this.groupedBy = Array.isArray(groupedBy) ? groupedBy : [groupedBy];
        return this._fetch(this.groupedBy);
    },
    /**
     * @override
     * @param {any} handle this parameter is ignored
     * @param {Object} params
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        if (params === 'special') {
            return Promise.resolve();
        }
        params = params || {};
        if ('context' in params) {
            var old_context = this.context;
            this.context = params.context;
            if (old_context.grid_anchor !== undefined || params.context.grid_anchor !== undefined) {
                this.context.grid_anchor = old_context.grid_anchor || params.context.grid_anchor;
            }
        }
        if ('domain' in params) {
            this.domain = params.domain;
        }
        if ('pagination' in params) {
            _.extend(this.context, params.pagination);
        }
        if ('range' in params) {
            this.currentRange = _.findWhere(this.ranges, {name: params.range});
        }
        if ('groupBy'in params) {
            if (params.groupBy.length) {
                    this.groupedBy = Array.isArray(params.groupBy) ? params.groupBy : [params.groupBy];
                } else {
                    this.groupedBy = this.rowFields;
                }
            }
        return this._fetch(this.groupedBy);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _enqueue: function (fn) {
        var self = this;
        this._waitingDef = $.Deferred();
        if (this._getPending) {
            // if there's already a query waiting for a slot, drop it and replace
            // it by the new updated query
            this._getPending = fn;
        } else {
            // if there's no query waiting for a slot, add the current one and
            // enqueue a fetch job
            this._getPending = fn;
            this._getMutex.exec(function () {

                var def = self._waitingDef;
                var fn = self._getPending;
                self._getPending = null;

                return fn().then(def.resolve.bind(def));
            });
        }
        return this._waitingDef;
    },
    /**
     * @private
     * @param {string[]} groupBy
     * @returns {Deferred}
     */
    _fetch: function(groupBy) {
            var self = this;
            if (!this.currentRange) {
                return Promise.resolve();
            }
            return this._getMutex.exec(function() {
                if (self.sectionField && self.sectionField === groupBy[0]) {
                    return self._getGroupedData(groupBy);
                } else {
                    return self._getUngroupedData(groupBy);
                }
            });
        },
    /**
     * @private
     * @param {string[]} groupBy
     * @returns {Deferred}
     */
    _getGroupedData: function (groupBy) {
        var self = this;
        return this._rpc({
            model: self.modelName,
            method: 'read_grid_domain',
            kwargs: {
                field: self.colField,
                range: self.currentRange,
            },
            context: self.getContext(),
        }).then(function (d) {
            return self._rpc({
                model: self.modelName,
                method: 'read_group',
                kwargs: {
                    domain: d.concat(self.domain || []),
                    fields: [self.sectionField],
                    groupby: [self.sectionField],
                },
                context: self.getContext()
            });
        }).then(function (groups) {
            if (!groups.length) {
                // if there are no groups in the output we still need
                // to fetch an empty grid so we can render the table's
                // decoration (pagination and columns &etc) otherwise
                // we get a completely empty grid
                return self._fetchSectionGrid(groupBy, {
                    __domain: self.domain || [],
                });
            }
            return $.when.apply(null, _(groups).map(function (group) {
                return self._fetchSectionGrid(groupBy, group);
            }));
        }).then(function () {
            var results = [].slice.apply(arguments);
            self._gridValue = results;
            self._gridValue.groupBy = groupBy;
            self._gridValue.colField = self.colField;
            self._gridValue.cellField = self.cellField;
            self._gridValue.range = self.currentRange.name;
            self._gridValue.context = self.context;

            // set the prev & next in the state for grouped
            var r0 = results[0];
            self._gridValue.prev = r0 && r0.prev;
            self._gridValue.next = r0 && r0.next;
        });
    },
    /**
     * @private
     * @param {string[]} groupBy
     * @param {Object} sectionGroup
     * @param {Object} [additionalContext]
     * @returns {Deferred}
     */
    _fetchSectionGrid: function (groupBy, sectionGroup, additionalContext) {
        var self = this;
        return this._rpc({
            model: this.modelName,
            method: 'read_grid',
            kwargs: {
                row_fields: groupBy.slice(1),
                col_field: this.colField,
                cell_field: this.cellField,
                range: this.currentRange,
                domain: sectionGroup.__domain,
            },
            context: this.getContext(additionalContext),
        }).done(function (grid) {
            grid.__label = sectionGroup[self.sectionField];
        });
    },
    /**
     * @private
     * @param {string[]} groupBy
     * @returns {Deferred}
     */
    _getUngroupedData: function (groupBy) {
        var self = this;
        return this._rpc({
            model: self.modelName,
            method: 'read_grid',
            kwargs: {
                row_fields: groupBy,
                col_field: self.colField,
                cell_field: self.cellField,
                domain: self.domain,
                range: self.currentRange,
            },
            context: self.getContext(),
        })
        .then(function (result) {
            self._gridValue = result;
            self._gridValue.groupBy = groupBy;
            self._gridValue.colField = self.colField;
            self._gridValue.cellField = self.cellField;
            self._gridValue.range = self.currentRange.name;
            self._gridValue.context = self.context;
        });
    },
});

});
