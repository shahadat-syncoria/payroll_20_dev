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


def _sync_identification_id(cr):
    """Keep identification_id consistent between hr_employee and current hr_version.

    On v19, identification data can exist on the delegated hr.version side while
    this custom module also defines hr.employee.identification_id. During
    upgrades, one side may be empty depending on previous module state.
    """
    if not _column_exists(cr, "hr_employee", "identification_id"):
        _logger.warning(
            "syncoria_can_payroll post-migration: hr_employee.identification_id column not found"
        )
        return

    if not _column_exists(cr, "hr_version", "identification_id"):
        _logger.warning(
            "syncoria_can_payroll post-migration: hr_version.identification_id column not found"
        )
        return

    if not _column_exists(cr, "hr_employee", "current_version_id"):
        _logger.warning(
            "syncoria_can_payroll post-migration: hr_employee.current_version_id column not found"
        )
        return

    # Fill employee value from current version when employee side is empty.
    cr.execute(
        """
        UPDATE hr_employee he
           SET identification_id = hv.identification_id
          FROM hr_version hv
         WHERE hv.id = he.current_version_id
           AND COALESCE(he.identification_id, '') = ''
           AND COALESCE(hv.identification_id, '') <> ''
        """
    )
    copied_to_employee = cr.rowcount

    # Fill current version value from employee side when version side is empty.
    cr.execute(
        """
        UPDATE hr_version hv
           SET identification_id = he.identification_id
          FROM hr_employee he
         WHERE hv.id = he.current_version_id
           AND COALESCE(hv.identification_id, '') = ''
           AND COALESCE(he.identification_id, '') <> ''
        """
    )
    copied_to_version = cr.rowcount

    _logger.info(
        "syncoria_can_payroll post-migration: synchronized identification_id "
        "(employee<-version: %d, version<-employee: %d)",
        copied_to_employee,
        copied_to_version,
    )


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
    # _sync_identification_id(cr)
    _sync_contract_notes(cr)

    _logger.info("syncoria_can_payroll post-migration %s -> finished", version)

