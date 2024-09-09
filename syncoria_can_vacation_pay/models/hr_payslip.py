from odoo import fields, models, api, _


class VacationHrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    vacation_pay_req_ref = fields.Char('Vacation Pay Request', readonly=True, default="")


class VacationPayslip(models.Model):
    _inherit = 'hr.payslip'

    vac_pay_earned_amount = fields.Float("Vacation Pay Earned Amount",default=0.0)
    vac_pay_earned_taken = fields.Float("Vacation Pay Earned Amount Taken",default=0.0)

    def store_vacation_pay_amount(self):
        """
            1. Calculate vacation pay of 4% or 6% of the gross based on the employees' tenure (vacation pay configuration).
            This calculation needs to be done after each payslip is in paid state.
        """
        for rec in self:
            employee = rec.employee_id
            insurable_amount = rec.line_ids.filtered(lambda x: x.code=="I_Earning").total
            insurable_amount -=  rec.line_ids.filtered(lambda x: x.code=="ADJUST_VP").total
            stored_vac_pay_amount = (insurable_amount*(employee.allocated_vac_percentage/100))
            employee.ytd_vac_pay_amount_erp += stored_vac_pay_amount
            rec.vac_pay_earned_amount = stored_vac_pay_amount



    def _calculate_vacation_pay(self, vacation_duration,contract_id):
        print(vacation_duration)
        # get_gross = list(filter(lambda a: a.get('code') == 'GROSS', self._get_payslip_lines()))
        # amount = 0.00
        final_vac_amount = 0.0
        employee_worked_years = self.employee_id.get_employee_years()

        # if get_gross:
            # amount = get_gross[0].get('amount')
        amount = contract_id.wage*12
        hourly_amount =  contract_id.hourly_rate if contract_id.is_hourly else ((contract_id.wage*12) / (self.contract_id.resource_calendar_id.full_time_required_hours * 52))
        if hourly_amount > 0.0:
            # vacation_slab_id = self.env['hr.vacation.slab'].search(
            #     [
            #         ('start_year', '<=', employee_worked_years),
            #         ('end_year', '>=', employee_worked_years)
            #     ], limit=1
            # )
            # final_vac_amount = ((amount*(vacation_slab_id.leave_percentage/100))/(vacation_slab_id.allocated_leave*8))*(vacation_duration*8)

            """
                    According to Meeting on 18 Aug. 
                    For timely accrual process vacation amount calculation will be (hourly rate * taken_vacation_hourly)
            """
            final_vac_amount = hourly_amount*(vacation_duration*8)


        return final_vac_amount

    def compute_sheet(self):
        # if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
        input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        for payslip in payslips:
            try:
                des_name = ","
                calculate_vacation_pay = 0.00
                employee_id = payslip.employee_id
                vacation_pay_ids = payslip.env['hr.vacation.pay'].search(
                    [('employee_id', '=', employee_id.id)]).filtered(
                    lambda x: x.state == 'validate' and  payslip.date_to >= x.date)
                if self.env["ir.config_parameter"].sudo().get_param(
                        'syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
                    calculate_vacation_pay = payslip._calculate_vacation_pay(sum(vacation_pay_ids.mapped('duration')),payslip.contract_id)
                if self.env["ir.config_parameter"].sudo().get_param(
                        'syncoria_can_vacation_pay.vac_pay_type') == 'cash_wise':
                    calculate_vacation_pay = sum(vacation_pay_ids.mapped('vacation_pay_amount'))
                if vacation_pay_ids and calculate_vacation_pay > 0.0:
                    payslip.input_line_ids.filtered(lambda x: x.input_type_id.id == input_type).unlink()
                    payslip.write({'input_line_ids': [(0, 0, {
                        'input_type_id': input_type,
                        'name': des_name.join(vacation_pay_ids.mapped('name')) or "",
                        'vacation_pay_req_ref': des_name.join(vacation_pay_ids.mapped('name')),
                        'amount': abs(calculate_vacation_pay),
                    })]})

                # ==================== Ajusted Vacation Pay ==============================
                if payslip.employee_id.is_adjust_vacation_pay_leave:
                    unpaid_days = sum(payslip.worked_days_line_ids.filtered(
                        lambda x: x.work_entry_type_id.deduct_from_gross and x.work_entry_type_id.is_leave).mapped(
                        'number_of_days'))
                    vacation_pay_one_day_hour = payslip.contract_id.resource_calendar_id.hours_per_day
                    hourly_rate = round((payslip.contract_id.wage * 12) / (
                            payslip.contract_id.resource_calendar_id.full_time_required_hours * 52), 2)
                    adjust_vac_pay_amount = (unpaid_days * vacation_pay_one_day_hour) * hourly_rate

                    adjusted_input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_adjusted_vac_pay').id
                    payslip.write({'input_line_ids': [(0, 0, {
                        'input_type_id': adjusted_input_type,
                        'name': "Adjusted Vacation Pay With Leave",
                        'amount': adjust_vac_pay_amount,
                    })]})
            except Exception as e:
                payslip.message_post(body=f"Vacation Pay Error:{e}")

        return super(VacationPayslip, self).compute_sheet()
    def vacation_pay_paid(self):
        input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id
        adjusted_input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_adjusted_vac_pay').id
        vacation_pay_req = self.env['hr.vacation.pay']
        for rec in self:
            vacation_pay_input_line_ids = rec.input_line_ids.filtered(lambda x: x.input_type_id.id == input_type)
            if rec.state == 'paid' and vacation_pay_input_line_ids:
                vacation_pay_req_ids = vacation_pay_input_line_ids.vacation_pay_req_ref.split(
                    ',') if vacation_pay_input_line_ids.vacation_pay_req_ref else []
                total_amount = 0.0
                for vpr in vacation_pay_req_ids:
                    vpr_id = vacation_pay_req.search([('name', '=', vpr)], limit=1)
                    if vpr_id:
                        vpr_id.vacation_pay_amount = vacation_pay_input_line_ids.amount
                        vpr_id.payslip_id = rec.id
                        vpr_id.action_paid()
                        total_amount += vpr_id.vacation_pay_amount

                rec.vac_pay_earned_taken = total_amount

            adjusted_vacation_pay_input_line_ids = rec.input_line_ids.filtered(lambda x: x.input_type_id.id == adjusted_input_type)
            if rec.state == 'paid' and adjusted_vacation_pay_input_line_ids:
                rec.vac_pay_earned_taken = sum(adjusted_vacation_pay_input_line_ids.mapped("amount"))

    def action_payslip_paid(self):
        res = super(VacationPayslip, self).action_payslip_paid()
        for rec in self:
            rec.vacation_pay_paid()
            if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type') == 'cash_wise':
                rec.store_vacation_pay_amount()
                rec.employee_id.update_vac_pay_amount_erp()


        return res

    def _cancel_vacation_pay_request(self):
        for rec in self:
            input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id
            vacation_pay_req = self.env['hr.vacation.pay']
            vacation_pay_input_line_ids = rec.input_line_ids.filtered(lambda x: x.input_type_id.id == input_type)
            if vacation_pay_input_line_ids:
                vacation_pay_req_ids = vacation_pay_input_line_ids.vacation_pay_req_ref.split(
                    ',') if vacation_pay_input_line_ids.vacation_pay_req_ref else []

                for vpr in vacation_pay_req_ids:
                    vpr_id = vacation_pay_req.search([('name', '=', vpr)], limit=1)
                    if vpr_id:
                        vpr_id.vacation_pay_amount = vacation_pay_input_line_ids.amount
                        vpr_id.payslip_id = rec.id
                        vpr_id.action_cancel()
                        rec.vac_pay_earned_taken = 0.00
                vacation_pay_input_line_ids.unlink()

    def write(self, vals):
        res = super(VacationPayslip,self).write(vals)
        for rec in self:
            # This commented because write function hits first then calculation happened
            # if 'state' in vals and vals.get('state') == 'paid':
            #     rec.employee_id.update_vac_pay_amount_erp()
            if 'state' in vals and vals.get('state') == 'cancel':
                rec.vac_pay_earned_amount = 0.00
                rec.vac_pay_earned_taken = 0.00
                rec._cancel_vacation_pay_request()
                rec.employee_id.update_vac_pay_amount_erp()
                rec.message_post(body="Related Vacation Pay Request Cancelled")
        return res

    # ------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------
    # Task : Add vacation information on Payslip
    # Responsible person : Maisha Umama

    def calculate_remaining_vac_leave_amount(self,total_taken_leave):
        """
            This function is for calculating remain vacation leave in amount.
            Where amount depends on current hourly rate.
        """
        self.ensure_one()
        contract = self.employee_id.contract_id
        hourly_rate = (contract.wage * 12) / (contract.resource_calendar_id.full_time_required_hours * 52)

        total_amount = round(hourly_rate * (total_taken_leave * contract.resource_calendar_id.hours_per_day),3) or 0.0

        return total_amount

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _reconcile_payments(self, to_process, edit_mode=False):
        res = super()._reconcile_payments(to_process, edit_mode=edit_mode)
        if self.env.context.get('hr_payroll_payment_register'):
            payslip = self.env['hr.payslip'].browse(self.env.context['hr_payroll_payment_register'])
            payslip.vacation_pay_paid()
            if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type') == 'cash_wise':
                payslip.store_vacation_pay_amount()
            payslip.employee_id.update_vac_pay_amount_erp()
        return res
