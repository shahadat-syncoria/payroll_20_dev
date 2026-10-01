# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslipWorkedDaysHelper(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('work_entry_type_id', 'number_of_days', 'number_of_hours', 'payslip_id')
    @api.depends_context('lang')
    def _compute_name(self):
        # v20: `name` is computed here (non-stored), so the native computation must still run
        super()._compute_name()
        for worked_days in self:
            try:
                avg_working_hour_per_day = worked_days.version_id.resource_calendar_id.hours_per_day
                worked_days.number_of_days = worked_days.number_of_hours / avg_working_hour_per_day
            except ZeroDivisionError:
                pass
