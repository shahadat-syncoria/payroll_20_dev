from odoo import fields,models,api


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays,self)._compute_amount()

        for rec in self:
            if rec.payslip_id.contract_id.is_hourly and rec.payslip_id.contract_id.work_entry_source == 'timesheet_hours' and rec.code==self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').code:
                rec.amount = rec.number_of_hours * rec.payslip_id.contract_id.hourly_rate
