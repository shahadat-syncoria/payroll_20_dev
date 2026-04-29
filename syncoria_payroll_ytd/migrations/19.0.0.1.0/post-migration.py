# Copyright (C) https://www.syncoria.com/
# support@syncoria.com
# Syncoria Inc.
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration placeholder — all tasks moved to pre-migration."""
    if not version:
        return
    _logger.info("syncoria_payroll_ytd post-migration %s → nothing to do", version)
