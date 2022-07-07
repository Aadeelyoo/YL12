# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_dashboard_validator = None
@view_validation.validate('dashboard')
def schema_dashboard(arch):
    """ Check the dashboard view against its schema

    :type arch: etree._Element
    """
    global _dashboard_validator

    if _dashboard_validator is None:
        with misc.file_open(os.path.join('dashboard_view', 'rng', 'dashboard_view.rng')) as f:
            _dashboard_validator = etree.RelaxNG(etree.parse(f))

    if _dashboard_validator.validate(arch):
        return True
        
    for error in _dashboard_validator.error_log:
        _logger.error(ustr(error))
    return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: