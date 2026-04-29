# Copyright (C) https://www.syncoria.com/
# support@syncoria.com
# Syncoria Inc.

import logging

_logger = logging.getLogger(__name__)


def _delete_report_payslip_inherit(cr):
    """Delete the qweb view syncoria_payroll_ytd.report_payslip_inherit
    so Odoo recreates it cleanly on upgrade.
    """
    _logger.info(
        "syncoria_payroll_ytd pre-migration: removing report_payslip_inherit"
    )

    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE type = 'qweb'
           AND EXISTS (
               SELECT 1 FROM ir_model_data
                WHERE model  = 'ir.ui.view'
                  AND name   = 'report_payslip_inherit'
                  AND module = 'syncoria_payroll_ytd'
                  AND res_id = ir_ui_view.id
           )
        """
    )
    _logger.info(
        "syncoria_payroll_ytd pre-migration: deleted %d qweb view(s)", cr.rowcount
    )

    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE model  = 'ir.ui.view'
           AND name   = 'report_payslip_inherit'
           AND module = 'syncoria_payroll_ytd'
        """
    )
    _logger.info(
        "syncoria_payroll_ytd pre-migration: cleaned up ir.model.data entry, rows=%d",
        cr.rowcount,
    )


def migrate(cr, version):
    """Pre-migration script for syncoria_payroll_ytd 19.0.0.1.0.

    Tasks performed:
    1. Delete qweb view report_payslip_inherit so Odoo recreates it cleanly
       on upgrade.
    """

    if not version:
        return

    _logger.info("syncoria_payroll_ytd pre-migration %s → starting", version)

    _delete_report_payslip_inherit(cr)

    _logger.info("syncoria_payroll_ytd pre-migration %s → finished", version)