from odoo import fields,models,api


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays,self)._compute_amount()

        for rec in self:
            # ================================== Calculation for manually input overtime =================
            if rec.code==self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').code  and not rec.payslip_id.contract_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                            rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                overtime_hour_rate = (current_hourly_rate*(overtime_pay_percent/100))
                rec.amount = rec.number_of_hours * overtime_hour_rate
            if rec.code==self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').code  and  rec.payslip_id.contract_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.payslip_id.contract_id.hourly_rate
                overtime_hour_rate = (current_hourly_rate*(overtime_pay_percent/100))
                rec.amount = rec.number_of_hours * overtime_hour_rate

                # ================================== Calculation for manually input Statutory overtime =================
            if rec.code == self.env.ref(
                    'syncoria_can_overtime.sync_stat_overtime_work_entry_type').code and not rec.payslip_id.contract_id.is_hourly:
                stat_overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_stat_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                        rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                stat_overtime_hour_rate = (current_hourly_rate * (stat_overtime_pay_percent / 100))
                rec.amount = rec.number_of_hours * stat_overtime_hour_rate
            if rec.code == self.env.ref(
                    'syncoria_can_overtime.sync_stat_overtime_work_entry_type').code and rec.payslip_id.contract_id.is_hourly:
                stat_overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_stat_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.payslip_id.contract_id.hourly_rate
                stat_overtime_hour_rate = (current_hourly_rate * (stat_overtime_pay_percent / 100))
                rec.amount = rec.number_of_hours * stat_overtime_hour_rate
