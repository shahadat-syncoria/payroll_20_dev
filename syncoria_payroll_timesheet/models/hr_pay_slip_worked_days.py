from odoo import fields,models,api


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'version_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays,self)._compute_amount()

        for rec in self:
            if rec.payslip_id.version_id.work_entry_source == 'timesheet_hours' and rec.code==self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').code:
                if rec.payslip_id.version_id.is_hourly:
                    rec.amount = rec.number_of_hours * rec.payslip_id.version_id.hourly_wage
                else:
                    hourly_wage = (rec.payslip_id.version_id.wage * 12) / (
                            rec.payslip_id.version_id.resource_calendar_id.full_time_required_hours * 52)
                    # rec.amount =  rec.payslip_id.version_id.contract_wage * rec.number_of_hours / (rec.payslip_id.sum_worked_hours or 1) if rec.payslip_id.version_id.is_fixed else hourly_wage * rec.number_of_hours
                    rec.amount = rec.payslip_id.version_id.paycycle_wage if rec.payslip_id.version_id.is_fixed else hourly_wage * rec.number_of_hours



