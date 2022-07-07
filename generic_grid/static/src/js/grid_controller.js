odoo.define('generic_grid.GridController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var config = require('web.config');
var dialogs = require('web.view_dialogs');
var utils = require('web.utils');
var concurrency = require('web.concurrency');

var qweb = core.qweb;
var _t = core._t;

var GridController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        'cell_edited': '_onCellEdited',
    }),
    events: {
        'click .o_grid_cell_information': '_onCellClick',
        'focus .o_grid_input': 'onGridFocus',
    },

    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.set('title', params.title);
        this.context = params.context;
        this.navigationButtons = params.navigationButtons;
        this.ranges = params.ranges;
        this.currentRange = params.currentRange;
        this.formViewID = params.formViewID;
        this.listViewID = params.listViewID;
        this.adjustment = params.adjustment;
        this.adjustName = params.adjustName;
        this.canCreate = params.activeActions.create;
        this.mutex = new concurrency.Mutex();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('grid.GridArrows', {
            widget: {
                _ranges: this.ranges,
                _buttons: this.navigationButtons,
                allowCreate: this.canCreate,
            },
            isMobile: config.device.isMobile
        }));
        this.$buttons.appendTo($node);
        this._updateButtons();
        this.$buttons.on('click', '.o_button_add_grid', this._onAddLine.bind(this));
        this.$buttons.on('click', '.grid_previous_arrow', this._onPagination.bind(this, 'prev'));
        this.$buttons.on('click', '.grid_initial_button', this._onPagination.bind(this, 'initial'));
        this.$buttons.on('click', '.grid_next_arrow', this._onPagination.bind(this, 'next'));
        this.$buttons.on('click', '.grid_range_arrow', this._onRangeChange.bind(this));
        this.$buttons.on('click', '.grid_button_arrow', this._onButtonClicked.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
     _grid_adjust: function(cell, newValue) {
            var difference = newValue - cell.value;
            if (Math.abs(difference) < 1e-6) {
                return Promise.resolve();
            }
            var state = this.model.get();
            var domain = this.model.domain.concat(cell.row.domain);
            var self = this;
            return this.mutex.exec(function() {
                return self._rpc({
                    model: self.modelName,
                    method: self.adjustName,
                    args: [[], domain, state.colField, cell.col.values[state.colField][0], state.cellField, difference],
                    context: self.model.getContext()
                }).then(function() {
                    return self.model.reload();
                }).then(function() {
                    var state = self.model.get();
                    return self.renderer.updateState(state, {});
                }).then(function() {
                    self._updateButtons(state);
                });
            });
        },

    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _update: function () {
        return this._super.apply(this, arguments)
            .then(this._updateButtons.bind(this));
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (this.$buttons) {
            var state = this.model.get();
            this.$buttons.find('.grid_previous_arrow').toggleClass('hidden', !state.prev);
            this.$buttons.find('.grid_next_arrow').toggleClass('hidden', !state.next);
            this.$buttons.find('.grid_initial_button').toggleClass('hidden', !state.initial);
            this.$buttons.find('.grid_range_arrow[data-name=' + this.currentRange + ']')
                    .addClass('active')
                    .siblings().removeClass('active');
        }
    },

    _onAddLine: function (event) {
        event.preventDefault();

        var context = this.model.getContext();
        var formContext = _.extend({}, context, {view_grid_add_line: true});
        var viewID = false;
        var view =  _.findWhere(this.actionViews, {type: 'form'})
        if (view) {
            viewID = view.viewID;
        }

        new dialogs.FormViewDialog(this, {
            res_model: this.modelName,
            res_id: false,
            context: formContext,
            view_id: viewID,
            title: _t("Add a Line"),
            disable_multiple_selection: true,
            on_saved: this.reload.bind(this, {}),
        }).open();
    },

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onCellEdited: function(event) {
            var state = this.model.get();
            this._grid_adjust({
                row: utils.into(state, event.data.row_path),
                col: utils.into(state, event.data.col_path),
                value: utils.into(state, event.data.cell_path).value,
            }, event.data.value).then(function() {
                if (event.data.doneCallback !== undefined) {
                    event.data.doneCallback();
                }
            })
        },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onButtonClicked: function (e) {
        var self = this;
        e.stopPropagation();
        var button = this.navigationButtons[$(e.target).attr('data-index')];
        var actionData = _.extend(button, {
            context: this.model.getContext(button.context),
        });
        this.model.getResIds().then(function (ids) {
            self.trigger_up('execute_action', {
                action_data: actionData,
                env: {
                    context: self.model.getContext(),
                    model: self.modelName,
                    resIDs: ids,
                },
                on_closed: self.reload.bind(self),
            });
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onCellClick: function (e) {
        var $target = $(e.target);
        var cell_path = $target.parent().attr('data-path').split('.');
        var row_path = cell_path.slice(0, -3).concat(['rows'], cell_path.slice(-2, -1));
        var state = this.model.get();
        var cell = utils.into(state, cell_path);
        var row = utils.into(state, row_path);

        var groupFields = state.groupBy.slice(_.isArray(state) ? 1 : 0);
        var label = _.map(groupFields, function (g) {
            return row.values[g][1] || _t('Undefined');
        }).join(': ');

        this.do_action({
            type: 'ir.actions.act_window',
            name: label,
            res_model: this.modelName,
            views: [
                [this.listViewID, 'list'],
                [this.formViewID, 'form']
            ],
            domain: cell.domain,
            context: this.context,
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    onGridFocus: function (e) {
        var selection = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(e.target);
        selection.removeAllRanges();
        selection.addRange(range);
    },
    /**
     * @private
     * @param {string} dir either 'prev', 'initial' or 'next
     */
    _onPagination: function (dir) {
        var state = this.model.get();
        if (state[0]) {
            this.update({pagination: state[0][dir]});
        } else {
            this.update({pagination: state[dir]});
        }
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onRangeChange: function (e) {
        e.stopPropagation();
        var $target = $(e.target);
        if ($target.hasClass('active')) {
            return;
        }
        this.currentRange = $target.attr('data-name');
        this.update({range: this.currentRange});
    },
});

return GridController;

});
