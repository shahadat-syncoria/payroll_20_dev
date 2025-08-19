from odoo import api, models,fields


class InheritedHrPaySlip(models.Model):
    _inherit = "hr.payslip"

    timesheet_count = fields.Integer(compute="_compute_timesheet_count")

    def _get_new_worked_days_lines(self):

        res = super()._get_new_worked_days_lines()
        for payslip in self:
            if payslip.employee_id and payslip.contract_id  and payslip.contract_id.work_entry_source == 'timesheet_hours':
                employee = payslip.employee_id
                avg_working_hour_per_day = payslip.contract_id.resource_calendar_id.hours_per_day
                employees_grid_data = [{
                    'id': employee.id,
                    'display_name': employee.name,
                    'grid_row_index': 0}]

                working_hours = employee.get_timesheet_and_working_hours_for_employees(
                    payslip.date_from.__str__(), payslip.date_to.__str__())

                timesheet_hours = working_hours.get(employee.id).get("worked_hours")

                res.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').id,
                    'name': 'Timesheet Log',
                    'number_of_days': timesheet_hours/avg_working_hour_per_day,
                    'number_of_hours': timesheet_hours,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
                attendance_type_id = self.env.ref('hr_work_entry.work_entry_type_attendance').id
                res = [entry for entry in res if entry[2]['work_entry_type_id'] != attendance_type_id]

        return res

    def _compute_timesheet_count(self):
        for slip in self:
            if slip.employee_id and slip.date_from and slip.date_to:
                slip.timesheet_count = self.env['account.analytic.line'].search_count([
                    ('employee_id', '=', slip.employee_id.id),
                    ('date', '>=', slip.date_from),
                    ('date', '<=', slip.date_to)
                ])
            else:
                slip.timesheet_count = 0

    def action_open_employee_timesheets(self):
        self.ensure_one()
        return {
            'name': 'Timesheets',
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to)
            ],
            'context': {
                'default_employee_id': self.employee_id.id
            }
        }

    def compute_workdays_manual_input(self, manual_input_ids):
        super(InheritedHrPaySlip, self).compute_workdays_manual_input(manual_input_ids)
        for rec in self:

            manual_input_line_id = manual_input_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            timesheet_hour = manual_input_line_id.attendance_hours
            avg_working_hour_per_day = rec.contract_id.resource_calendar_id.hours_per_day
            work_entry_id = self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').id

            existing_line = rec.worked_days_line_ids.filtered(
                lambda l: l.work_entry_type_id.id == work_entry_id
            )
            worked_days_lines = []

            if timesheet_hour and  rec.contract_id.work_entry_source == "timesheet_hours":
                if existing_line:
                    existing_line.write({
                        'number_of_days': timesheet_hour / avg_working_hour_per_day,
                        'number_of_hours': timesheet_hour,
                        'name': 'Attendance',
                    })
                else :
                    rec.write({
                        'worked_days_line_ids': [(0, 0, {
                            'work_entry_type_id': work_entry_id,
                            'name': 'Timesheet Log',
                            'number_of_days': timesheet_hour / avg_working_hour_per_day,
                            'number_of_hours': timesheet_hour,
                        })]
                    })

            rec.worked_days_line_ids = worked_days_lines