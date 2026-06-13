# Copyright (C) https://www.syncoria.com/
# support@syncoria.com
# Syncoria Inc.

import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = %s
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


def _ensure_backup_table(cr):
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS syncoria_hr_payslip_number_backup (
            payslip_id INTEGER PRIMARY KEY,
            number VARCHAR
        )
        """
    )


def _backup_payslip_number(cr):
    """Preserve hr.payslip.number before hr_payroll v19 drops the core field."""
    _ensure_backup_table(cr)

    if not _column_exists(cr, "hr_payslip", "number"):
        _logger.warning(
            "syncoria_can_payroll pre-migration: hr_payslip.number column not found; "
            "skipping backup (already upgraded or empty database)"
        )
        return

    cr.execute(
        """
        INSERT INTO syncoria_hr_payslip_number_backup (payslip_id, number)
        SELECT id, number
          FROM hr_payslip
         WHERE COALESCE(number, '') <> ''
        ON CONFLICT (payslip_id) DO UPDATE
           SET number = EXCLUDED.number
        """
    )
    _logger.info(
        "syncoria_can_payroll pre-migration: backed up %d payslip reference numbers",
        cr.rowcount,
    )


def migrate(cr, version):
    if not version:
        return

    _logger.info("syncoria_can_payroll pre-migration %s -> starting", version)
    _backup_payslip_number(cr)
    _logger.info("syncoria_can_payroll pre-migration %s -> finished", version)
