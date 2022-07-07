# -*- coding: utf-8 -*-
import logging
import os

from lxml import etree
from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_GridValidator = None


@view_validation.validate('grid')
def schema_grid(arch):
    """ Check the grid view against its schema

    :type arch: etree._Element
    """
    global _GridValidator

    if _GridValidator is None:
        with misc.file_open(os.path.join('generic_grid', 'views', 'grid.rng')) as f:
            _GridValidator = etree.RelaxNG(etree.parse(f))

    if _GridValidator.validate(arch):
        return True

    for error in _GridValidator.error_log:
        _logger.error(ustr(error))
    return False


@view_validation.validate('grid')
def valid_field_types(arch):
    """ Each of the row, col and measure <field>s must appear once and only
    once in a grid view

    :type arch: etree._Element
    """
    types = {'col', 'measure'}
    for f in arch.iterdescendants('field'):
        field_type = f.get('type')
        if field_type == 'row':
            continue

        if field_type in types:
            types.remove(field_type)
        else:
            return False

    return True
