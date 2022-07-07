# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Dashboard View',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Build your own dashboard view for any Odoo object',
    'description': """
Dashboard
=========

Like pivot and graph view, The dashboard view is used to display aggregate data.
However, the dashboard can embed sub views, which makes it possible to have a
more complete and interesting look on a given dataset.

The dashboard view can display sub views, aggregates for some fields (over a
domain), or even *formulas* (expressions which involves one or more aggregates).
For example, here is a very simple dashboard:

.. code-block:: xml

<dashboard>
    <view type="graph" ref="sale.view_order_product_graph"/>
        <group>
              <group>
                    <aggregate name="price_subtotal_confirmed_orders" string="Total Sales" field="price_total" help="Total, Tax Included" widget="monetary"/>
                    <aggregate name="price_subtotal_all_orders" string="Untaxed Total" field="price_subtotal" widget="monetary"/>
                    <aggregate name="order_id_confirmed_orders" field="order_id" string="Orders"/>
                    <formula name="total" string="Average Order" value="record.price_subtotal_confirmed_orders / record.order_id_confirmed_orders" widget=“monetary"/>
              </group>
              <group>
                    <widget name="pie_chart" title="Sales Teams" attrs="{'groupby': 'team_id'}"/>
              </group>
        </group>
    <view type="pivot" ref="sale_dashboard.sale_report_view_pivot"/>
</dashboard>

**The root element of the Dashboard view is <dashboard>, it does not accept any
attributes.**


**There are 5 possible type of tags in a dashboard view:**

view
----
    Declares a sub view.

    Admissible attributes are:

    - *type* (mandatory)
        The type of the sub view.  For example, *graph* or *pivot*.

    - *ref* (optional)
        An xml id for a view. If not given, the default view for the model will
        be used.

    - *name* (optional)
        A string which identifies this element.  It is mostly
        useful to be used as a target for an xpath.
        
    E.g.    
        
    .. code-block:: xml
        
    <view type="graph" ref=“sale.view_order_product_graph"/>
    <view type="pivot" ref="sale_dashboard.sale_report_view_pivot"/>     

group
-----
    Defines a column layout.  This is actually very similar to the group element
    in a form view.

    Admissible attributes are:

    - *string* (optional)
        A description which will be displayed as a group title.

    - *colspan* (optional)
        The number of subcolumns in this group tag. By default, 6.

    - *col* (optional)
        The number of columns spanned by this group tag (only makes sense inside
        another group). By default, 6.
        
    E.g.
    
    .. code-block:: xml

    <group col="12">
      <group colspan=“3”>
        …
        …
      </group>
      <group colspan="1" col=“12”>
        …
        …
      </group>
    </group>

aggregate
---------
    Declares an aggregate.  This is the value of an aggregate for a given field
    over the current domain.

    Note that aggregates are supposed to be used inside a group tag (otherwise
    the style will not be properly applied).

    Admissible attributes are:

    - ``field`` (mandatory)
        The field name to use for computing the aggregate. Possible field types
        are:

        - ``integer`` (default group operator is sum)
        - ``float``  (default group operator is sum)
        - ``many2one`` (default group operator is count distinct)

    - ``name`` (mandatory)
        A string to identify this aggregate (useful for formulas)

    - ``string`` (optional)
        A short description that will be displayed above the value. If not
        given, it will fall back to the field string.

    - ``domain`` (optional)
        An additional restriction on the set of records that we want to aggregate.
        This domain will be combined with the current domain.

    - ``domain_label`` (optional)
        When the user clicks on an aggregate with a domain, it will be added to
        the search view as a facet.  The string displayed for this facet can
        be customized with this attribute.

    - ``group_operator`` (optional)
        A valid postgreSQL aggregate function identifier to use when aggregating
        values (see https://www.postgresql.org/docs/9.5/static/functions-aggregate.html).
        If not provided, By default, the group_operator from the field definition is used.
        Note that no aggregation of field values is achieved if the group_operator value is "".

        **Note** 
        
        The special aggregate function ``count_distinct`` (defined in odoo) can also be used here

        .. code-block:: xml

          <aggregate name="order_id_confirmed_orders" field="order_id" string=“Orders" group_operator="count_distinct"/> 



    - ``col`` (optional)
        The number of columns spanned by this tag (only makes sense inside a
        group). By default, 1.

    - ``widget`` (optional)
        A widget to format the value (like the widget attribute for fields).
        For example, monetary.

    - ``help`` (optional)
        A help message to dipslay in a tooltip (equivalent of help for a field in python)

    - ``measure`` (optional)
        This attribute is the name of a field describing the measure that has to be used
        in the graph and pivot views when clicking on the aggregate.
        The special value __count__ can be used to use the count measure.

        .. code-block:: xml

          <aggregate name="customers" string="# Customers" field="partner_id" group_operator="count" measure="__count__"/>

    - ``clickable`` (optional)
        A boolean indicating if this aggregate should be clickable or not (default to true).
        Clicking on a clickable aggregate will change the measures used by the subviews
        and add the value of the domain attribute (if any) to the search view.

    - ``value_label`` (optional)
        A string put on the right of the aggregate value.
        For example, it can be useful to indicate the unit of measure
        of the aggregate value.

formula
-------
    Declares a derived value.  Formulas are values computed from aggregates.

    Note that like aggregates, formulas are supposed to be used inside a group
    tag (otherwise the style will not be properly applied).

    Admissible attributes are:

    - ``value`` (mandatory)
        A string expression that will be evaluated, with the builtin python
        evaluator (in the web client).  Every aggregate can be used in the
        context, in the ``record`` variable.  For example,
        ``record.price_total / record.order_id``.

    - ``name`` (optional)
        A string to identify this formula

    - ``string`` (optional)
        A short description that will be displayed above the formula.

    - ``col`` (optional)
        The number of columns spanned by this tag (only makes sense inside a
        group). By default, 1.

    - ``widget`` (optional)
        A widget to format the value (like the widget attribute for fields).
        For example, monetary. By default, it is 'float'.

    - ``help`` (optional)
        A help message to dipslay in a tooltip (equivalent of help for a field in python)

    - ``value_label`` (optional)
        A string put on the right of the formula value.
        For example, it can be useful to indicate the unit of measure
        of the formula value.
        
    E.g.
    
    .. code-block:: xml
    
    <formula name="total" string="Average Order" value="record.price_subtotal_confirmed_orders / record.order_id_confirmed_orders" widget=“monetary"/>

widget
------
    Declares a specialized widget to be used to display the information. This is
    a mechanism similar to the widgets in the form view.

    Admissible attributes are:

    - ``name`` (mandatory)
        A string to identify which widget should be instantiated. The view will
        look into the ``widget_registry`` to get the proper class.

    - ``col`` (optional)
        The number of columns spanned by this tag (only makes sense inside a
        group). By default, 1.
        
    E.g.
    
    .. code-block:: xml    
    
    <widget name="pie_chart" title="Sales Teams" attrs="{'groupby': 'team_id'}"/>

""",
    'author': 'Gritxi Consulting Services Pvt. Ltd',    
    'depends': ['base', 'web'],
    'data': ['views/dashboard_templates.xml'],
    'qweb': [
        'static/src/xml/tooltip.xml',        
        'static/src/xml/templates.xml',
    ],
    'images': [
        'static/description/main_screenshot.png'
    ],
    'price': 145,
    'currency': 'EUR',
    'license': 'OPL-1',
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: