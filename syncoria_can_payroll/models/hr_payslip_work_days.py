from odoo import fields,models,api


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays,self)._compute_amount()

        for rec in self:
            if rec.payslip_id.contract_id.is_hourly:
                hourly_rate = rec.payslip_id.contract_id.hourly_rate
            else:
                hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                                rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
            if rec.payslip_id.struct_id not in rec.work_entry_type_id.unpaid_structure_ids:
                if not rec.work_entry_type_id.is_leave:
                    # rec.amount =  rec.payslip_id.contract_id.contract_wage * rec.number_of_hours / (rec.payslip_id.sum_worked_hours or 1) if rec.payslip_id.contract_id.is_fixed else hourly_rate * rec.number_of_hours
                    rec.amount = rec.payslip_id.contract_id.paycycle_wage if rec.payslip_id.contract_id.is_fixed else hourly_rate * rec.number_of_hours
                if  rec.work_entry_type_id.is_leave:
                    rec.amount = hourly_rate * rec.number_of_hours
                # if  rec.work_entry_type_id.is_leave and rec.work_entry_type_id.is_negative_amount:
                #     rec.amount = -(hourly_rate * rec.number_of_hours)
