import json

from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError

class InheritedHrPayslipOvertime(models.Model):
    _inherit = 'hr.payslip'

    def compute_workdays_manual_input(self, manual_input_ids):
        super(InheritedHrPayslipOvertime,self).compute_workdays_manual_input(manual_input_ids)
        for rec in self:

            manual_input_line_id = manual_input_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            over_time_hour = manual_input_line_id.overtime_hours
            stat_over_time_hour = manual_input_line_id.stat_overtime_hours
            avg_working_hour_per_day = rec.contract_id.resource_calendar_id.hours_per_day
            worked_days_lines = []
            if over_time_hour > 0.0:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
                    'name': 'Overtime',
                    'number_of_days': over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': over_time_hour,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            if stat_over_time_hour>0.0:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_stat_overtime_work_entry_type').id,
                    'name': 'Statutory Holidays Overtime',
                    'number_of_days': stat_over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': stat_over_time_hour,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            rec.worked_days_line_ids = worked_days_lines