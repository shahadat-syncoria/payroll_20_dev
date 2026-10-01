from odoo import fields,models,api
from ..helper.helper_functions import iso_weeks_in_year


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'version_id.wage', 'version_id.hourly_wage',
                 'payslip_id.sum_worked_hours', 'work_entry_type_id.amount_rate', 'work_entry_type_id.is_extra_hours',
                 'employee_id.paycycle_wage')
    def _compute_amount(self):

        super(SyncoriaWorkedDays, self)._compute_amount()

        for rec in self:
            # same guard as the core method: never touch edited / non draft payslips
            if rec.payslip_id.edited or rec.payslip_id.state != 'draft':
                continue
            weeks_in_year = iso_weeks_in_year(rec.payslip_id.year)
            if rec.payslip_id.employee_id.is_hourly:
                hourly_wage = rec.employee_id.hourly_wage
            else:
                hourly_wage = rec.payslip_id.fixed_wage_hourly_rate
            if rec.is_paid:
                if rec.work_entry_type_id.code in ["002.00", "TIMESHEET_WORK100"]:
                    # rec.amount =  rec.payslip_id.version_id.contract_wage * rec.number_of_hours / (rec.payslip_id.sum_worked_hours or 1) if rec.payslip_id.version_id.is_fixed else hourly_wage * rec.number_of_hours
                    rec.amount = rec.payslip_id.employee_id.paycycle_wage if rec.payslip_id.employee_id.is_fixed else hourly_wage * rec.number_of_hours
                if rec.work_entry_type_id.count_as == 'absence':
                    rec.amount = hourly_wage * rec.number_of_hours
                # if  rec.work_entry_type_id.is_leave and rec.work_entry_type_id.is_negative_amount:
                #     rec.amount = -(hourly_wage * rec.number_of_hours)
