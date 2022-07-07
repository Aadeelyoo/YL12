from odoo import api, fields, models
from collections import OrderedDict, Counter

IS_ODOO_VERSION_BEFORE_v11 = False



class DashboardWidgetGraph(models.AbstractModel):
    _inherit = 'is.dashboard.widget.abstract'

    def chart_get_data(self, dom, model, measure_field, groupby, show_empty_groups, action, title=False, orderby=False):
        if not model or not groupby:
            return False  # Not enough data to make a chart/graph

        if groupby:
            groupby = list(filter(lambda g: g[0], groupby))  # Remove any empty groups

        data = self.get_query_result(model, dom, measure_field, groupby=groupby, orderby=orderby)

        def get_groupby_domain_value(item):
            item = get_first_item_if_list(item)
            # Return the first value of the groupby field in the domain
            if item:
                dom = list(filter(lambda dom: dom[0] == groupby[0][0], item['__domain']))
                if dom:
                    field = dom[0][0]
                    value = dom[0][2]

                    value = get_string_for_field_selection_value(field, value) or value
                    return value

                # return list(filter(lambda dom: dom[0] == groupby[0][0], item['__domain']))[0][2] if list(filter(lambda dom: dom[0] == groupby[0][0], item['__domain'])) else False
            return False

        def get_first_item_if_list(item):
            if not IS_ODOO_VERSION_BEFORE_v11 and isinstance(item, filter):
                item = list(item)
            if not item:
                return False
            if isinstance(item, list):
                return item[0]
            return item

        def get_second_item_if_tuple(item):
            if not IS_ODOO_VERSION_BEFORE_v11 and isinstance(item, filter):
                item = list(item)
            if not item:
                return False
            if isinstance(item, tuple) and len(item) > 1:
                return item[1]
            return item

        def _get_label(item):
            if group_field not in item:
                return "Unknown"

            if isinstance(item[group_field], tuple) and len(item[group_field]) == 2:
                return item[group_field][1]
            elif group_field in item:
                if group_field in self.env[model.model]._fields:
                    field = self.env[model.model]._fields[group_field]
                    if field.type == 'selection':
                        l = [l[1] for l in field.selection if l[0] == item[group_field]]
                        if l:
                            return l[0]
                return get_string_for_field_selection_value(group_field, item[group_field]) or item[group_field]

        def get_string_for_field_selection_value(field_name, value):
            if field_name not in self.env[model.model]._fields:
                return False

            field = self.env[model.model]._fields[field_name]
            if field.type == 'selection':
                l = [l[1] for l in field.selection if l[0] == value]
                if l:
                    return l[0]
            return False

        def first(iterable, condition=lambda x: True):
            """
            https://stackoverflow.com/questions/2361426/get-the-first-item-from-an-iterable-that-matches-a-condition/2361899

            Returns the first item in the `iterable` that
            satisfies the `condition`.

            If the condition is not given, returns the first item of
            the iterable.

            Raises `StopIteration` if no item satysfing the condition is found.

            >> first( (1,2,3), condition=lambda x: x % 2 == 0)
            2
            >> first(range(3, 100))
            3
            >> first( () )
            Traceback (most recent call last):
            ...
            StopIteration
            """

            return next(x for x in iterable if condition(x))

        if not data:
            return data
        if not len(groupby):
            return False
        if len(groupby) > 2:
            raise UserWarning("More than 2 group by fields is not supported")
        elif len(groupby) == 1:
            group_field = groupby[0][2]

            def _key_if_data_has_key(key):
                return key if data and key in data[0] else False

            value_field = _key_if_data_has_key(measure_field[0]) or _key_if_data_has_key(groupby[0][0] + "_count") or "__count"

            labels = list(map(lambda line: _get_label(line), data))
            values = list(map(lambda line: line.get(value_field, 0), data))
            domains = list(map(lambda line: line.get('__domain'), data))


            if groupby and groupby[0] and groupby[0][3] and groupby[0][3].ttype in ['datetime', 'date']:
                date_start = list(map(lambda line: get_groupby_domain_value(line), data))
            else:
                date_start = False

            datasets = [{
                'label': title,
                'data': list(values),
                'domains': list(domains),
                'date_start': list(date_start) if date_start else [],
                'action_id': action.id,
                'model': model.model,
            }]

            return {
                'labels': list(map(lambda label: get_second_item_if_tuple(label), labels)),
                'dates': list(date_start) if date_start else [],
                'datasets': datasets,
            }

        elif len(groupby) == 2:
            group_field = groupby[0][2]
            value_field = measure_field[0] or "__count"

            # Get group values and sort by total value in each group (Odoo does not sort this way in read_group)
            group_values = set([d[group_field] for d in data])  # Get list of all the options in the group
            group_values = {g: sum([d[value_field] for d in data if d[group_field] == g]) for g in group_values}  # Create a dict of each option with the total value
            reverse = ' DESC' in orderby  # TODO: Handle this better
            group_values = sorted(group_values, key=group_values.get, reverse=reverse)  # Sort by the total value and just keep the keys

            group2_field = groupby[1][2]
            group2_values = set([d[group2_field] for d in data])

            label_data_old = set(map(lambda item: (item[group_field], get_groupby_domain_value(item) or _get_label(item)), data))

            def first_group_data(group_value):
                return first(data, lambda i: i[group_field] == group_value)

            # Convert group_values into a dict with the value as the label
            label_data = [(g, get_groupby_domain_value(first_group_data(g) or _get_label(first_group_data(g)))) for g in group_values]

            if not orderby:
                # Get all labels in order by getting label/date-pair and sorting. If there is no date than sort by label name
                label_data = sorted(label_data, key=lambda item: item[1])
            labels = list(map(lambda item: item, label_data))

            if groupby and groupby[0] and groupby[0][3] and groupby[0][3].ttype in ['datetime', 'date']:
                dates = list(map(lambda item: item[1], label_data))
            else:
                dates = False

            datasets = []
            for group in group2_values:
                group_data = list(filter(lambda item: item[group_field] and item[group2_field] == group and (show_empty_groups or item[value_field]), data))

                def get_group_data_for_label(label):
                    return list(filter(lambda line: line[group_field] == label, group_data))

                def get_value_from_data(item, key, default=False):
                    item = get_first_item_if_list(item)
                    if item:
                        return item.get(key, default)
                    return default

                values = [get_value_from_data(get_group_data_for_label(label[0]), value_field, default=0) for label in labels]
                date_start = [get_groupby_domain_value(get_group_data_for_label(label[0])) for label in labels]
                domains = [get_value_from_data(get_group_data_for_label(label[0]), '__domain') for label in labels]

                datasets.append({
                    'label': get_second_item_if_tuple(group),
                    'data': values,
                    'domains': domains,
                    'date_start': date_start,
                    'action_id': action.id,
                    'model': model.model,
                })

            return {
                'labels': list(map(lambda label: get_second_item_if_tuple(label[0]), labels)),
                'dates': list(dates) if dates else [],
                'datasets': datasets,
            }
