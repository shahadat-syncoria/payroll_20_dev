from odoo import fields,models,api


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays,self)._compute_amount()

        for rec in self:
            if rec.payslip_id.contract_id.work_entry_source in ['attendance','calendar'] and rec.payslip_id.contract_id.is_hourly:
                rec.amount = rec.payslip_id.contract_id.hourly_rate * rec.number_of_hours
            if rec.payslip_id.contract_id.work_entry_source in ['attendance','calendar'] and not rec.payslip_id.contract_id.is_hourly:
                hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                            rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                rec.amount =  rec.payslip_id.contract_id.paycycle_wage if rec.payslip_id.contract_id.is_fixed else hourly_rate * rec.number_of_hours