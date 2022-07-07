# -*- coding: utf-8 -*-

import collections
import datetime
import time
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta, MO, SU
from functools import partial

import babel.dates
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_Pivot_TUP = [('pivot', "Pivot")]


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=_Pivot_TUP)


class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=_Pivot_TUP)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_pivot(self, row_fields, col_field, cell_field, domain=None, range=None):
        """
        Current anchor (if sensible for the col_field) can be provided by the
        ``pivot_anchor`` value in the context

        :param list[str] row_fields: group row header fields
        :param str col_field: column field
        :param str cell_field: cell field, summed
        :param range: displayed range for the current page
        :type range: None | {'step': object, 'span': object}
        :type domain: None | list
        :returns: dict of prev context, next context, matrix data, row values
                  and column values
        """
        domain = expression.normalize_domain(domain)
        column_info = self._pivot_column_info(col_field, range)

        groups = self._read_group_raw(
            expression.AND([domain, column_info.domain]),
            [col_field, cell_field],
            [column_info.grouping] + row_fields,
            lazy=False
        )

        row_key = lambda it, fs=row_fields: tuple(it[f] for f in fs)
        # [{ values: { field1: value1, field2: value2 } }]
        rows = self._pivot_get_row_headers(row_fields, groups, key=row_key)
        # column_info.values is a [(value, label)] seq
        # convert to [{ values: { col_field: (value, label) } }]
        cols = column_info.values

        # map of cells indexed by row_key (tuple of row values) then column value
        cell_map = collections.defaultdict(dict)
        for group in groups:
            row = row_key(group)
            col = column_info.format(group[column_info.grouping])
            cell_map[row][col] = self._pivot_format_cell(group, cell_field)

        # pre-build whole pivot, row-major, h = len(rows), w = len(cols),
        # each cell is
        #
        # * size (number of records)
        # * value (accumulated cell_field)
        # * domain (domain for the records of that cell
        pivot = []
        for r in rows:
            row = []
            pivot.append(row)
            r_k = row_key(r['values'])
            for c in cols:
                col_value = c['values'][col_field][0]
                it = cell_map[r_k].get(col_value)
                if it:  # accumulated cell exists, just use it
                    row.append(it)
                else:
                    # generate de novo domain for the cell
                    # The domain of the cell is the combination of the domain of the row, the
                    # column and the view.
                    d = expression.AND([r['domain'], c['domain'], domain])
                    row.append(self._pivot_make_empty_cell(d))
                row[-1]['is_current'] = c.get('is_current', False)

        return {
            'prev': column_info.prev,
            'next': column_info.next,
            'initial': column_info.initial,
            'cols': cols,
            'rows': rows,
            'pivot': pivot,
        }

    def _pivot_make_empty_cell(self, cell_domain):
        return {'size': 0, 'domain': cell_domain, 'value': 0}

    def _pivot_format_cell(self, group, cell_field):
        return {
            'size': group['__count'],
            'domain': group['__domain'],
            'value': group[cell_field],
        }

    def _pivot_get_row_headers(self, row_fields, groups, key):
        seen = {}
        rows = []
        for cell in groups:
            k = key(cell)
            if k in seen:
                seen[k][1].append(cell['__domain'])
            else:
                r = (
                    {f: cell[f] for f in row_fields},
                    [cell['__domain']],
                )
                seen[k] = r
                rows.append(r)

        # TODO: generates pretty long domains, is there a way to simplify them?
        return [
            {'values': values, 'domain': expression.OR(domains)}
            for values, domains in rows
        ]

    def _pivot_column_info(self, name, range):
        """
        :param str name:
        :param range:
        :type range: None | dict
        :rtype: ColumnMetadata
        """
        if not range:
            range = {}
        field = self._fields[name]
        context_anchor = self.env.context.get('pivot_anchor')

        if field.type == 'selection':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                initial=False,
                values=[{
                    'values': {name: v},
                    'domain': [(name, '=', v[0])],
                    'is_current': False
                } for v in field._description_selection(self.env)
                ],
                format=lambda a: a,
            )
        elif field.type == 'many2one':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                initial=False,
                values=[{
                    'values': {name: v},
                    'domain': [(name, '=', v[0])],
                    'is_current': False
                } for v in self.env[field.comodel_name].search([]).name_get()
                ],
                format=lambda a: a and a[0],
            )
        elif field.type == 'date':
            # seemingly sane defaults
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            today = anchor = field.from_string(field.context_today(self))
            if context_anchor:
                anchor = field.from_string(context_anchor)

            labelize = self._get_date_formatter(
                step, locale=self.env.context.get('lang', 'en_US'))
            r = self._pivot_range_of(span, step, anchor)
            period_prev, period_next = self._pivot_pagination(field, span, step, anchor)
            return ColumnMetadata(
                grouping='{}:{}'.format(name, step),
                domain=[
                    '&',
                    (name, '>=', field.to_string(r.start)),
                    (name, '<=', field.to_string(r.end))
                ],
                prev=period_prev and {'pivot_anchor': period_prev, 'default_%s' % name: period_prev},
                next=period_next and {'pivot_anchor': period_next, 'default_%s' % name: period_next},
                initial=period_prev and period_next and {'pivot_anchor': field.to_string(today),
                                                         'default_%s' % name: field.to_string(today)},
                values=[{
                    'values': {
                        name: (
                            "%s/%s" % (field.to_string(d), field.to_string(d + self._pivot_step_by(step))),
                            labelize(d)
                        )},
                    'domain': ['&',
                               (name, '>=', field.to_string(d)),
                               (name, '<', field.to_string(d + self._pivot_step_by(step)))],
                    'is_current': (
                    (d.month == today.month and d.year == today.year) if step == 'month' else d == today),
                } for d in r.iter(step)
                ],
                format=lambda a: a and a[0],
            )
        else:
            raise ValueError(_("Can not use fields of type %s as pivot columns") % field.type)

    @api.model
    def read_pivot_domain(self, field, range):
        """ JS pivot view may need to know the "span domain" of the pivot before
        it has been able to read the pivot at all. This provides only that part
        of the pivot processing

        .. warning:: the result domain *must* be properly normalized
        """
        if not range:
            range = {}
        field = self._fields[field]
        if field.type == 'selection':
            return []
        elif field.type == 'many2one':
            return []
        elif field.type == 'date':
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            anchor = field.from_string(field.context_today(self))
            context_anchor = self.env.context.get('pivot_anchor')
            if context_anchor:
                anchor = field.from_string(context_anchor)

            r = self._pivot_range_of(span, step, anchor)
            return [
                '&',
                (field.name, '>=', field.to_string(r.start)),
                (field.name, '<=', field.to_string(r.end))
            ]
        raise UserError(_("Can not use fields of type %s as pivot columns") % field.type)

    def _get_date_formatter(self, step, locale):
        """ Returns a callable taking a single positional date argument and
        formatting it for the step and locale provided.
        """
        if hasattr(babel.dates, 'format_skeleton'):
            def _format(d, _fmt=babel.dates.format_skeleton, _sk=SKELETONS[step], _l=locale):
                result = _fmt(datetime=d, skeleton=_sk, locale=_l)
                # approximate distribution over two lines, for better
                # precision should be done by rendering with an actual
                # proportional font, for even better precision should be done
                # using the fonts the browser asks for, here we just use
                # non-whitespace length which is really gross. Also may need
                # word-splitting in non-latin scripts.
                #
                # also ideally should not split the lines at all under a
                # certain width
                cl = lambda l: sum(len(s) for s in l)
                line1 = result.split(u' ')
                halfway = cl(line1) / 2.
                line2 = collections.deque(maxlen=int(halfway) + 1)
                while cl(line1) > halfway:
                    line2.appendleft(line1.pop())

                middle = line2.popleft()
                if cl(line1) < cl(line2):
                    line1.append(middle)
                else:
                    line2.appendleft(middle)

                return u"%s\n%s" % (
                    u'\u00A0'.join(line1),
                    u'\u00A0'.join(line2),
                )

            return _format
        else:
            return partial(babel.dates.format_date,
                           format=FORMAT[step],
                           locale=locale)

    def _pivot_pagination(self, field, span, step, anchor):
        if field.type == 'date':
            diff = self._pivot_step_by(span)
            period_prev = field.to_string(anchor - diff)
            period_next = field.to_string(anchor + diff)
            return period_prev, period_next
        return False, False

    def _pivot_step_by(self, span):
        return STEP_BY.get(span)

    def _pivot_range_of(self, span, step, anchor):
        return date_range(self._pivot_start_of(span, step, anchor),
                          self._pivot_end_of(span, step, anchor))

    def _pivot_start_of(self, span, step, anchor):
        return anchor + START_OF[span]

    def _pivot_end_of(self, span, step, anchor):
        return anchor + END_OF[span]

    @api.multi
    def adjust_pivot(self, domain, cell_field, change, header_dict):

        new_domain = []
        date_interval = [':day', ':month', ':quarter', ':week', ':year']
        lines = self.search(domain)
        for dom in domain:
            if not dom in new_domain and isinstance(dom, list):
                new_domain.append(dom)

        if not lines:
            try:
                lines.create({
                    cell_field: change
                })
            except Exception:
                vals = {k: v for d in list(map(lambda dom: {dom[0]: dom[2]}, new_domain)) for k, v in d.items()}
                context = {k: v for d in list(map(lambda dom: {'default_' + dom[0]: dom[2]}, new_domain)) for k, v in
                           d.items()}
                context.update({
                    'default_' + cell_field: change,
                })

                for key in header_dict:
                    res = any(ele in key for ele in date_interval)
                    is_week = any(ele in key for ele in [':week'])
                    is_quarter = any(ele in key for ele in [':quarter'])

                    if res:
                        field = 'default_' + key.split(':')[0]
                        val_field = key.split(':')[0]
                        date_string = header_dict[key]
                        week_quarter = date_string.split()
                        try:
                            context[field] = parse(date_string, dayfirst=True)
                            vals[val_field] = parse(date_string, dayfirst=True)
                        except Exception:
                            if is_week:
                                year = week_quarter[1]
                                # as it starts with 0 and you want week to start from Monday
                                WEEK = int(week_quarter[0].replace('W', '')) - 1
                                startdate = time.asctime(time.strptime(year + ' %d 1' % WEEK, '%Y %W %w'))
                                startdate = datetime.datetime.strptime(startdate, '%a %b %d %H:%M:%S %Y')
                                context[field] = startdate + datetime.timedelta(days=0)
                                vals[val_field] = startdate + datetime.timedelta(days=0)

                            elif is_quarter:
                                year = week_quarter[1]
                                Q = int(week_quarter[0].replace('Q', ''))
                                context[field] = datetime.datetime(int(year), 3 * Q - 2, 1)
                                vals[val_field] = datetime.datetime(int(year), 3 * Q - 2, 1)

                data = {
                    'context': context,
                    'vals': vals
                }
                return data

        elif len(lines) > 1:
            res = lines[0].copy()
            res.write({
                cell_field: change
            })
        else:
            lines.write({
                cell_field: lines[cell_field] + change
            })

        return

    @api.multi
    def update_data(self, res_id, model, vals, data):
        record = self.env[model].search([('id', '=', res_id)])
        list_val = list(vals.keys())
        list_data = list(data.keys())
        for data in list_data:
            if data in list_val:
                list_val.remove(data)

        for val in list_val:
            record.write({val: vals.get(val)})

        return res_id


ColumnMetadata = collections.namedtuple('ColumnMetadata', 'grouping domain prev next initial values format')


class date_range(object):
    def __init__(self, start, stop):
        assert start < stop
        self.start = start
        self.end = stop

    def iter(self, step):
        v = self.start
        step = STEP_BY[step]
        while v <= self.end:
            yield v
            v += step


START_OF = {
    'week': relativedelta(weekday=MO(-1)),
    'month': relativedelta(day=1),
    'year': relativedelta(yearday=1),
}
END_OF = {
    'week': relativedelta(weekday=SU),
    'month': relativedelta(months=1, day=1, days=-1),
    'year': relativedelta(years=1, yearday=1, days=-1),
}
STEP_BY = {
    'day': relativedelta(days=1),
    'week': relativedelta(weeks=1),
    'month': relativedelta(months=1),
    'year': relativedelta(years=1),
}

FORMAT = {
    'day': u"EEE\nMMM\u00A0dd",
    'month': u'MMMM\u00A0yyyy',
}
SKELETONS = {
    'day': u"MMMEEEdd",
    'month': u'yyyyMMMM',
}
