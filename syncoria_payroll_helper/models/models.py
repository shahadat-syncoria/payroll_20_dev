# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslipWorkedDaysHelper(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('number_of_hours')
    def _compute_name(self):
        for worked_days in self:
            try:
                avg_working_hour_per_day = worked_days.contract_id.resource_calendar_id.hours_per_day
                worked_days.number_of_days = worked_days.number_of_hours / avg_working_hour_per_day
            except:
                pass
