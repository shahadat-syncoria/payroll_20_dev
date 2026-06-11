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

def _sync_contract_notes(cr):
    """Migrate notes from hr_contract to hr_version."""

    if not _column_exists(cr, "hr_contract", "notes"):
        _logger.warning("hr_contract.notes column not found")
        return

    if not _column_exists(cr, "hr_version", "notes"):
        _logger.warning("hr_version.notes column not found")
        return

    cr.execute("""
        UPDATE hr_version hv
           SET notes = hc.notes
          FROM hr_contract hc
         WHERE hv.id = hc.id
           AND COALESCE(hv.notes, '') = ''
           AND COALESCE(hc.notes, '') <> ''
    """)

    _logger.info(
        "Migrated contract notes to version notes (%d records)",
        cr.rowcount,
    )


def migrate(cr, version):
    if not version:
        return

    _logger.info("syncoria_can_payroll post-migration %s -> starting", version)

    _sync_contract_notes(cr)

    _logger.info("syncoria_can_payroll post-migration %s -> finished", version)

