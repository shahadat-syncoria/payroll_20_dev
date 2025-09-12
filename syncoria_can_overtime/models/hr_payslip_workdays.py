from odoo import fields,models,api,_
from odoo.exceptions import UserError, ValidationError


class SyncoriaWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'


    # @api.constrains("number_of_hours")
    # def _check_overtime_hour(self):
    #     overtime_work_entry = self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type')
    #     for rec in self:
    #         if rec.code == overtime_work_entry.code and rec.number_of_hours > rec.payslip_id.total_stored_overtime:
    #             raise UserError(_("Overtime can not be greater then stored overtime."))

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):

        super(SyncoriaWorkedDays, self)._compute_amount()

        for rec in self:
            lines = rec.payslip_id.contract_id.overtime_threshold_id.line_ids

            for line in lines:

                if line.work_entry_id.code == rec.code:
                    overtime_pay_percent = line.overtime_rate
                    if not rec.payslip_id.contract_id.is_hourly:
                        current_hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                                rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                    else:
                        current_hourly_rate = rec.payslip_id.contract_id.hourly_rate
                    overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
                    rec.amount = rec.number_of_hours * overtime_hour_rate

            # ================================== Calculation for manually input overtime =================
            if rec.code in [self.env.ref(
                    'syncoria_can_overtime.sync_overtime_work_entry_type').code,self.env.ref(
                    'syncoria_can_overtime.sync_banked_overtime_work_entry_type').code] and not rec.payslip_id.contract_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = (rec.payslip_id.contract_id.wage * 12) / (
                        rec.payslip_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
                rec.amount = rec.number_of_hours * overtime_hour_rate
            if rec.code in [self.env.ref(
                    'syncoria_can_overtime.sync_overtime_work_entry_type').code,self.env.ref(
                    'syncoria_can_overtime.sync_banked_overtime_work_entry_type').code] and rec.payslip_id.contract_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.payslip_id.contract_id.hourly_rate
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
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



class SyncoriaHrVacation(models.Model):
    _inherit = "hr.payslip.input"

    @api.constrains("amount")
    def banked_overtime_amount(self):
        overtime_input_type = self.env.ref('syncoria_can_overtime.input_ca_bank_overtime').id
        for rec in self:
            if rec.payslip_id.employee_id.overtime_method =='banked_overtime' and rec.input_type_id.id == overtime_input_type and rec.amount > round(rec.payslip_id.total_stored_overtime_amount,2):
                raise ValidationError(_("Requested overtime greater than stored banked overtime amount!!"))
