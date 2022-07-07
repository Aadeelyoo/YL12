odoo.define('generic_pivot.PivotController', function (require) {
'use strict';

var PivotController = require('web.PivotController');
var PivotView = require('web.PivotView');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');
var dialogs = require('web.view_dialogs');
var utils = require('web.utils');
var concurrency = require('web.concurrency');

var _t = core._t;
var QWeb = core.qweb;


PivotController.include({
    events: _.extend({}, PivotController.prototype.events, {
       'keypress .o_pivot_edit':"_onPivotKeypress",
    }),

    custom_events: _.extend({}, PivotController.prototype.custom_events, {
        'cell_edited': '_onCellEdited',
    }),

    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.adjustment = params.adjustment;
        this.adjustName = params.adjustName;
        this.mutex = new concurrency.Mutex();
    },

    _onPivotKeydown:  function (event) {
        if (event.keyCode == 9) {       // tab pressed
                event.preventDefault(); // stops its action
            }
        },

    _onPivotKeypress:  function (event) {
        var $target = this.target;
        var keyCode = event.which;
        var flag = /^[\d]*[.:]?[\d]*$/.test(event.key);                                         // specific key pressed
        if ($target && (event.key == ':' || event.key == '.' )) {
            if ($target[0].innerText.includes(':') || $target[0].innerText.includes('.')) {
                flag = false                                                                    // stops its action
            }
        }
        return flag;
    },

    renderButtons: function ($node) {
         this._super.apply(this, arguments);
         var view =  _.findWhere(this.actionViews, {type: 'form'});
         if(!view){
            this.$buttons.find('.o_pivot_button_add').css({"display":"none"});
            this.$buttons.find('.o_pivot_button_add').removeClass('o_pivot_button_add');
            $('#add_btn').hide();
         }
         else{
            $('#add_btn').show();
            this.$buttons.on('click', '.o_pivot_button_add', this._onAddLine.bind(this));
         }
    },

    _onAddLine: function (event) {
        event.preventDefault();
        var viewID = false;
        var view =  _.findWhere(this.actionViews, {type: 'form'})
        if (view) {
            viewID = view.viewID;
        }
        var context = this.initialState.context;
        var formContext = _.extend({}, context, {view_pivot_add_line: true});

        new dialogs.FormViewDialog(this, {
            res_model: this.modelName,
            res_id: false,
            view_id: viewID,
            context: formContext,
            title: _t("Add a Line"),
            disable_multiple_selection: true,
            on_saved: this.reload.bind(this, {}),
        }).open();
    },

    timeStringToFloat: function (val) {
        if (val.includes(":")) {
            var hoursMinutes = val.split(/[.:]/);
            var hours = parseInt(hoursMinutes[0], 10);
            var minutes = hoursMinutes[1] ? parseInt(hoursMinutes[1], 10) : 0;
            return hours + minutes / 60;
        } else {
            val = val.replace(/,/g, '');
            return parseFloat(val);
        }
    },

    // To set a focus and curse on cell
    onPivotfocus: function (e) {
        var selection = window.getSelection();
        var range = document.createRange();
        range.collapse(true);
        selection.addRange(range);
        e.target.focus();
    },

    _onCellClick: function (event) {
        var $target = $(event.currentTarget);
        if ($target.hasClass('o_pivot_header_cell_closed') ||
            $target.hasClass('o_pivot_header_cell_opened') ||
            $target.hasClass('o_empty') ||
            $target.data('type') === 'variation' ||
            !this.enableLinking) {
            return;
        }
        var self = this;
        var state = this.model.get(this.handle);
        var colDomain, rowDomain;
        this.header_dict = {};
        var index = 1;
        var row_index = 1;
        var colgroupbys = this.model.getHeader($target.data('col_id')).root.groupbys;
        var rowgroupbys = this.model.getHeader($target.data('id')).root.groupbys;

        _.each(colgroupbys, function (colby) {
            if (colby) {
                self.header_dict[colby] = self.model.getHeader($target.data('col_id')).path[index];
            }
            index += 1;
        });

        _.each(rowgroupbys, function (rowby) {
            if (rowby) {
                self.header_dict[rowby] = self.model.getHeader($target.data('id')).path[row_index];
            }
            row_index += 1;
        });

        if ($target.data('type') === 'comparisonData') {
            colDomain = this.model.getHeader($target.data('col_id')).comparisonDomain || [];
            rowDomain = this.model.getHeader($target.data('id')).comparisonDomain || [];
        } else {
            colDomain = this.model.getHeader($target.data('col_id')).domain || [];
            rowDomain = this.model.getHeader($target.data('id')).domain || [];
        }
        this.domain_col = colDomain;
        this.domain_row = rowDomain;
        this.target = $target;
        var context = _.omit(state.context, function (val, key) {
            return key === 'group_by' || _.str.startsWith(key, 'search_default_');
        });

        this.cell_old_value = this.timeStringToFloat($target[0].innerText);

        if ($target.hasClass('o_pivot_col')){
            var previous_element = document.querySelectorAll('[contenteditable=true]');
            _.each(previous_element, function (elem) {
                if (elem.parentNode != $target[0]) {
                    elem.setAttribute('contenteditable', false);
                    elem.parentElement.classList.remove('o_pivot_cell_search')
                }
            });
            $target.find('div.o_pivot_edit').attr('contenteditable', true);
            this.onPivotfocus(event);
            $target.addClass('o_pivot_cell_search');
        } else {
            self.do_action({
                type: 'ir.actions.act_window',
                name: self.title,
                res_model: self.modelName,
                views: self.views,
                view_type: 'list',
                view_mode: 'list',
                target: 'current',
                context: context,
                domain: state.domain.concat(rowDomain, colDomain),
            })
        }

        $('.o_pivot_cell_information').click(function () {
            self.do_action({
                type: 'ir.actions.act_window',
                name: self.title,
                res_model: self.modelName,
                views: self.views,
                view_type: 'list',
                view_mode: 'list',
                target: 'current',
                context: context,
                domain: state.domain.concat(rowDomain, colDomain),
            });
        });

    },

    _adjust: function(cell, data) {
        var difference = data.value - cell.value;
        if (Math.abs(difference) < 1e-6) {
            return Promise.resolve(false);
        }

        var state = this.model.get();
        var domain = state.domain.concat(cell.row_domain, cell.col_domain);
        var self = this;

        var viewID = false;
        var view =  _.findWhere(this.actionViews, {type: 'form'})
        if (view) {
            viewID = view.viewID;
        }
        return this.mutex.exec(function() {
            return self._rpc({
                model: self.modelName,
                method: self.adjustName,
                args: [[], domain, data.FieldName, difference, cell.header_dict],
                context: state.context
                }).then(function(result) {
                    if (result) {
                        var pop = new dialogs.FormViewDialog(self, {
                            res_model: self.modelName,
                            res_id: false,
                            view_id: viewID,
                            title: _t("Add new Record"),
                            context: result['context'],
                            disable_multiple_selection: true,
                            on_saved: function (record) {
                                self._rpc({
                                    model: 'base',
                                    method: 'update_data',
                                    args: [[], record.res_id, self.modelName, result['vals'], record.data],
                                }).then(function(res) {
                                    self.update({}, {reload: true});
                                });
                            },
                        }).open();
                        pop.on('closed', self, function () {
                            self.update({}, {reload: true});
                        });
                    } else {
                        return self.update({}, {reload: true});
                    }
                });
        });

    },

    _onCellEdited: function(event) {
        var state = this.model.get();
        if(this.domain_row && this.domain_col != undefined){
            this._adjust({
                row_domain: this.domain_row,
                col_domain: this.domain_col,
                value: this.cell_old_value,
                header_dict: this.header_dict,
            }, event.data)
            this.domain_row = this.domain_col = [];

            if(this.target){
                this.target.removeClass('o_pivot_cell_search');
                this.target.find('div.o_pivot_edit').attr('contenteditable', false);
            }
        }
    },
});

});
