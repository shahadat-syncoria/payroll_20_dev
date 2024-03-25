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


    def _get_new_worked_days_lines(self):
        res = super()._get_new_worked_days_lines()
        overtime_hour = sum(self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee_id.id), ('date', '>=', self.date_from),('date', '<=', self.date_to)]).mapped('duration'))

        if overtime_hour:
            avg_working_hour_per_day = self.contract_id.resource_calendar_id.hours_per_day


            res.append((0, 0, {
                'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
                'name': 'Overtime',
                'number_of_days': overtime_hour / avg_working_hour_per_day,
                'number_of_hours': overtime_hour,
                # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

            }))
            new_worked_days_lines = []
            for entry in res:
                entry_data = entry[2]  # Extracting the dictionary from the tuple
                if entry_data['work_entry_type_id'] == self.env.ref(
                        'hr_work_entry.work_entry_type_attendance').id:  # Checking if work_entry_type_id is 8
                    real_attendance_hour = entry_data['number_of_hours'] - overtime_hour
                    entry_data['number_of_hours'] = real_attendance_hour  # Updating the number of hours to 10
                    entry_data[
                        'number_of_days'] = real_attendance_hour / avg_working_hour_per_day  # Updating the number of hours to 10
                new_worked_days_lines.append(entry)
                res = new_worked_days_lines
        return res


        # if self.struct_id.use_worked_day_lines:
        #     if not self.contract_id.time_credit:
        #         return [(0, 0, vals) for vals in self._get_worked_day_lines()]
        #     worked_days_line_values = self._get_worked_day_lines(domain=[('is_credit_time', '=', False)])
        #     for vals in worked_days_line_values:
        #         vals['is_credit_time'] = False
        #     credit_time_line_values = self._get_credit_time_lines()
        #     return [(0, 0, vals) for vals in worked_days_line_values + credit_time_line_values]
        # return []