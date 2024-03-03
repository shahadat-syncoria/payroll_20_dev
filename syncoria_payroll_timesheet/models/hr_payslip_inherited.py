from odoo import api, models


class InheritedHrPaySlip(models.Model):
    _inherit = "hr.payslip"

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_worked_days_line_ids(self):
        result = super(InheritedHrPaySlip, self)._compute_worked_days_line_ids()

        for payslip in self:
            if payslip.employee_id and payslip.contract_id and payslip.contract_id.is_hourly and payslip.contract_id.work_entry_source == 'timesheet_hours':
                employee = payslip.employee_id
                avg_working_hour_per_day = payslip.contract_id.resource_calendar_id.hours_per_day
                payslip.wage_type = "hourly"
                employees_grid_data = [{
                    'id': employee.id,
                    'display_name': employee.name,
                    'grid_row_index': 0}]

                working_hours = employee.get_timesheet_and_working_hours_for_employees(
                                                                                       payslip.date_from.__str__(), payslip.date_to.__str__())

                timesheet_hours = working_hours.get(employee.id).get("worked_hours")

                worked_days_lines = [(0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').id,
                    'name': 'Timesheet Log',
                    'number_of_days': timesheet_hours/avg_working_hour_per_day,
                    'number_of_hours': timesheet_hours,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                })]
                payslip.worked_days_line_ids = worked_days_lines
        return result
