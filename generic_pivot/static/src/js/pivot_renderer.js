odoo.define('generic_pivot.PivotRenderer', function (require) {
"use strict";

var PivotRenderer = require('web.PivotRenderer');
var core = require('web.core');
var field_utils = require('web.field_utils');

var _t = core._t;

PivotRenderer.include({

    events: {
        'blur .o_pivot_edit': "_onPivotDivBlur",
    },

     _parse: function (value) {
        var cellWidget = Object.values(this.fieldWidgets)
        if (cellWidget) {
            return field_utils.parse[cellWidget[0]](value);
        }
        var cellField = Object.keys(this.fieldWidgets);
        return field_utils.parse[cellField.type](value, cellField);
    },

    DateChecker: function (column) {
        var today = new Date();
        var check_datatype = new Date(column.innerText);
        var current_date = today.getFullYear()+'-'+(today.getMonth()+1)+'-'+today.getDate();
        var col_month = ((column.innerText).split(' '));
        var current_month = today.getMonth() + 1;
        var current_year = today.getFullYear();
        var column_date = new Date(column.innerText)
        var column_month = column_date.getMonth() + 1;
        var column_year = column_date.getFullYear();
        var filtered_date = column_year+'-'+(column_month)+'-'+column_date.getDate();
        var week_quarter_number = ((column.innerText).split(' ')[0]).slice(1)
        var week_quarter_year = (column.innerText).split(' ')[1]

        Date.prototype.getWeek = function() {
            { return $.datepicker.iso8601Week(this); }
        }

        var current_week_number = today.getWeek();
        var current_quarter = Math.floor((today.getMonth() + 3) / 3);

        if (check_datatype != 'Invalid Date') {
            if (col_month.length > 2) {
                if (current_date == filtered_date){
                    column.classList.add('highlight_cell')
                }
                return true
            }
            if ((current_month == column_month) && (current_year == column_year)){
                column.classList.add('highlight_cell')
            }
        } else {
            if ((current_week_number == week_quarter_number) && (current_year == week_quarter_year)){
                column.classList.add('highlight_cell')
            }

            if ((current_quarter == week_quarter_number) && (current_year == week_quarter_year)){
                column.classList.add('highlight_cell')
            }
        }
    },

    _renderHeaders: function ($thead, headers, nbrCols) {
        this._super.apply(this, arguments);
        var row_length = $thead[0].rows.length;
        for (var i = 0; i < row_length; i++) {
            var col_length = $thead[0].rows[i].cells.length;
            for (var j = 0; j < col_length; j++){
                var column = $thead[0].rows[i].cells[j];
                this.DateChecker(column);
            }
        }
    },

    _renderRows: function ($tbody, rows) {
        var self = this;
        var i, j, value, measure, name, formatter, $row, $cell, $header;
        var nbrMeasures = this.state.measures.length;
        var length = rows[0].values.length;
        var shouldDisplayTotal = this.state.mainColWidth > 1;

        var groupbyLabels = _.map(this.state.rowGroupBys, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });
        var measureTypes = this.state.measures.map(function (name) {
            var type = self.state.fields[name].type;
            return type === 'many2one' ? 'integer' : type;
        });

        for (i = 0; i < rows.length; i++) {
            $row = $('<tr>');
            $header = $('<td>')
                .text(rows[i].title)
                .data('id', rows[i].id)
                .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                .addClass(rows[i].expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');

            if (rows[i].indent > 0) $header.attr('title', groupbyLabels[rows[i].indent - 1]);
            $header.appendTo($row);
            for (j = 0; j < length; j++) {
                value = rows[i].values[j];
                name = this.state.measures[j % nbrMeasures];
                formatter = field_utils.format[this.fieldWidgets[name] || measureTypes[j % nbrMeasures]];
                measure = this.state.fields[name];
                if (this.compare) {
                    if (value instanceof Object) {
                        for (var origin in value) {
                            $cell = $('<td>')
                                .data('id', rows[i].id)
                                .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                .data('type' , origin)
                                .toggleClass('o_empty', false)
                                .addClass('o_pivot_cell_value o_pivot_col text-right');

                            if (origin === 'data') {
                                $cell.append($('<i>', {class: 'fa fa-search-plus o_pivot_cell_information'})).html();
                                if(name == '__count'){
                                    $cell.append($('<div>', {class: 'o_value', 'id': name}).html(formatter(value[origin], measure)));
                                    $cell.removeClass('o_pivot_col');
                                }
                                else{
                                    $cell.append($('<div>', {class: 'o_value o_pivot_edit', contentEditable: false, 'id': name}).html(formatter(value[origin], measure)));
                                }
                            } else if (origin === 'comparisonData') {
                                $cell.removeClass('o_pivot_col');
                                $cell.append($('<div>', {class: 'o_comparison_value'}).html(formatter(
                                    value[origin],
                                    measure
                                )));
                            } else {
                                $cell.append($('<div>', {class: 'o_variation' + value[origin].signClass}).html(
                                    field_utils.format.percentage(
                                        value[origin].magnitude,
                                        measure
                                    )
                                ));
                            }
                            if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                                $cell.css('font-weight', 'bold');
                                $cell.find('div.o_value').removeClass('o_pivot_edit');
                                $cell.removeClass('o_pivot_col');
                                var cell_length = ($cell.find('div.o_value')).length;
                                if (cell_length) {
                                    $cell.find('div.o_value')[0].contentEditable = false
                                }
                            }
                            $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                            $row.append($cell);
                        }
                    } else {
                        for (var l=0; l < 3; l++) {
                            $cell = $('<td>')
                                .data('id', rows[i].id)
                                .toggleClass('o_empty', true)
                                .addClass('o_pivot_cell_value text-right');
                            $row.append($cell);
                        }
                    }
                } else {
                    $cell = $('<td>')
                                .data('id', rows[i].id)
                                .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                .addClass('o_pivot_cell_value o_pivot_col text-right');
                    var cell_length = ($cell.find('div.o_value')).length;
                        $cell.append($('<i>', {class: 'fa fa-search-plus o_pivot_cell_information'})).html();
                        if(name == '__count'){
                            $cell.append($('<div>', {class: 'o_value', 'id': name}).html(formatter(value, measure)));
                            $cell.removeClass('o_pivot_col');
                        }
                        else{
                            if(value == undefined){
                                value = 0.0;
                            }
                            $cell.append($('<div>', {class: 'o_value o_pivot_edit', contentEditable: false, 'id': name}).html(formatter(value, measure)));
                        }
                    if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                        $cell.css('font-weight', 'bold');
                        $cell.find('div.o_value').removeClass('o_pivot_edit');
                        $cell.removeClass('o_pivot_col');
                        var cell_length = ($cell.find('div.o_value')).length;
                        if (cell_length) {
                            $cell.find('div.o_value')[0].contentEditable = false
                        }
                    }
                    $row.append($cell);

                    try {
                        this._parse($cell[0].textContent.trim());
                    } catch (_) {
                        $cell.removeClass('o_pivot_col');
                        $cell.find('div.o_value').removeClass('o_pivot_edit');
                        var cell_length = ($cell.find('div.o_value')).length;
                        if (cell_length) {
                            $cell.find('div.o_value')[0].contentEditable = false
                        }
                    }
                    $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                }
            }
            this.DateChecker($header[0]);
            $tbody.append($row);
        }
    },

    _render: function () {
        var result = this._super.apply(this, arguments);
        if (this.compare) {
           var o_value = this.$('.o_value');
           for (var index in o_value) {
               if (!isNaN(index)){
                   o_value.removeAttr('contenteditable');
                   o_value.removeClass('o_pivot_edit');
                   o_value.parent().removeClass('o_pivot_col');
                   var list = o_value[parseInt(index)];
               }
           }
        }

        return result
    },

    _onPivotDivBlur: function (event) {
        var $target = $(event.target);
        var value = 0;
        try {
            value = this._parse(event.target.textContent.trim());
            $target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        } catch (_) {
            $target.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return;
        }

        this.trigger_up('cell_edited', {
                $target,
                value: value,
                FieldName: $target[0].id,
            });
        value = 0;

        event.target.parentElement.classList.remove('o_pivot_cell_search')

    },

});

});
