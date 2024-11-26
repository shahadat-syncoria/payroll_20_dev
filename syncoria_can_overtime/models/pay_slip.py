import json
import logging
from datetime import timedelta, datetime, time

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api, Command
from odoo.exceptions import UserError, ValidationError
import pytz
_logger = logging.getLogger(__name__)

class OvertimeHrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    overtime_pay_req_ref = fields.Char('Overtime Pay Request', readonly=True, default="")

class InheritedHrPayslipOvertime(models.Model):
    _inherit = 'hr.payslip'

    total_stored_overtime = fields.Float("Stored Overtime Hours", related="employee_id.total_stored_overtime")
    total_stored_overtime_amount = fields.Float("Stored Overtime Hours",
                                                related="employee_id.total_stored_overtime_amount")

    def _check_banked_overtime_constrain(self, banked_overtime_other_input):
        self.ensure_one()
        if banked_overtime_other_input.amount > self.total_stored_overtime_amount:
            raise ValidationError(_("Requested overtime greater than stored banked overtime amount!!"))


    # ========================================= New Overtime Concept =============================================
    def _get_hourly_rate(self):
        for rec in self:
            if not rec.contract_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = (rec.contract_id.wage * 12) / (
                        rec.contract_id.resource_calendar_id.full_time_required_hours * 52)
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
            else:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.contract_id.hourly_rate
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))

            return overtime_hour_rate



    def calculate_overtime(self):
        _logger.info(f"Payslip ID===>{self.id}")
        overtime_hours = 0
        full_week_hours = self.contract_id.overtime_threshold
        # Get the start and end date of the payslip
        slip_tz = pytz.timezone(self.contract_id.resource_calendar_id.tz)
        utc = pytz.timezone('UTC')
        payslip_start_date = slip_tz.localize(datetime.combine(self.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
        # payslip_start_date = datetime.combine(self.date_from, time.min)
        payslip_end_date = slip_tz.localize(datetime.combine(self.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
        # payslip_end_date = datetime.combine(self.date_to, time.max)

        _logger.info(f"Start date:{payslip_start_date} and End Date: {payslip_end_date}")

        # Find the Monday of the start week and Sunday of the end week
        first_monday = payslip_start_date - timedelta(days=payslip_start_date.weekday())
        last_sunday = payslip_end_date

        _logger.info(f"First Monday:{first_monday} ")



        # Retrieve work entries for the payslip period
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', first_monday),
            ('date_stop', '<=', last_sunday),
            ('state','in',['draft','validated'])
        ])

        # Initialize week tracking
        # current_week_start = datetime.combine(first_monday, time.min)
        current_week_start = slip_tz.localize(datetime.combine(first_monday, time.min)).astimezone(utc).replace(tzinfo=None)
        # current_week_end = datetime.combine((current_week_start + timedelta(days=4)), time.max)
        current_week_end = slip_tz.localize(datetime.combine((current_week_start + timedelta(days=4)), time.max)).astimezone(utc).replace(tzinfo=None)
        first_week = True

        # Iterate through full weeks
        while current_week_start <= last_sunday:
            # Get work entries for the current week
            _logger.info(f"Week Start:{current_week_start} and current_week_end: {current_week_end} and IS first week:{first_week}")
            weekly_work_entries = work_entries.filtered(
                lambda we: we.date_start >= current_week_start and we.date_stop <= current_week_end
            )
            _logger.info(f"Weekly Work entries:{weekly_work_entries[-1].date_start if weekly_work_entries else None} and {weekly_work_entries[-1].date_stop if weekly_work_entries else None}\n")

            # Calculate weekly hours
            weekly_hours = sum(
                [(we.date_stop - we.date_start).total_seconds() / 3600 for we in weekly_work_entries]
            )
            _logger.info(f"Weekly Hour:{weekly_hours}\n")


            if weekly_hours > full_week_hours:
                # Handle partial weeks:
                # If the pay period starts in the middle of the week
                if payslip_start_date.weekday() != 0 and first_week:
                    _logger.info(f"First Partial Week===>")
                    first_partial_week_hours = sum(
                        [(we.date_stop - we.date_start).total_seconds() / 3600 for we in work_entries.filtered(
                            lambda we: we.date_start >= first_monday and we.date_stop < payslip_start_date
                        )]
                    )
                    _logger.info(f"First Partial Week Hour:{first_partial_week_hours} and Date Start: {first_monday} and End date:{payslip_start_date}")
                    if first_partial_week_hours > full_week_hours:
                        _logger.info(
                            f"first_partial_week_hours({first_partial_week_hours}) > full_week_hours{full_week_hours}")
                        first_partial_overtime_hours = first_partial_week_hours - full_week_hours
                        _logger.info(f"first_partial_overtime_hours({first_partial_overtime_hours})")
                        overtime_hours += (weekly_hours - full_week_hours) - first_partial_overtime_hours
                        _logger.info(f"first_partial_overtime_hours({(weekly_hours - full_week_hours) - first_partial_overtime_hours})")

                else:
                    overtime_hours += weekly_hours - full_week_hours

            # Move to the next week
            current_week_start += timedelta(days=7)
            # current_week_start = datetime.combine(current_week_start, time.min)
            current_week_start = slip_tz.localize(datetime.combine(current_week_start, time.min)).astimezone(utc).replace(tzinfo=None)
            _logger.info(f"Next Week Start: {current_week_start})")
            current_week_end = current_week_start + timedelta(days=4)
            # current_week_end = datetime.combine(current_week_end, time.max)
            current_week_end = slip_tz.localize(datetime.combine(current_week_end, time.max)).astimezone(utc).replace(tzinfo=None)
            first_week = False
            _logger.info(f"Next Week Ends: {current_week_end})")

        # Handle partial weeks:
        # If the pay period starts in the middle of the week
        # if payslip_start_date.weekday() != 0:
        #     first_partial_week_hours = sum(
        #         [(we.date_stop - we.date_start).total_seconds() / 3600 for we in work_entries.filtered(
        #             lambda we: we.date_start.date() < first_monday and we.date_stop.date() >= first_monday
        #         )]
        #     )
        #     if first_partial_week_hours > full_week_hours:
        #         overtime_hours += first_partial_week_hours - full_week_hours

        # If the pay period ends in the middle of the week
        # if payslip_end_date.weekday() != 5:
        #     last_partial_week_hours = sum(
        #         [(we.date_stop - we.date_start).total_seconds() / 3600 for we in work_entries.filtered(
        #             lambda we: we.date_start.date() > last_sunday and we.date_stop.date() <= last_sunday
        #         )]
        #     )
        #     if last_partial_week_hours > full_week_hours:
        #         overtime_hours += last_partial_week_hours - full_week_hours

        _logger.info(f"overtime_hours")
        return overtime_hours

    def _get_new_worked_days_lines(self):
        """
                Overtime added to workdays line
                This function will run if overtime_method is
        """
        res = super()._get_new_worked_days_lines()
        if self.employee_id.overtime_method in ['banked_overtime','paycycle_out'] and self.pay_cycle_period:
            overtime = self.calculate_overtime()
            avg_working_hour_per_day = self.contract_id.resource_calendar_id.hours_per_day
            if self.employee_id.overtime_method== 'banked_overtime' and  overtime>0:
                res.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_banked_overtime_work_entry_type').id,
                    'name': 'Overtime',
                    'number_of_days': overtime / avg_working_hour_per_day,
                    'number_of_hours': overtime,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            if self.employee_id.overtime_method == 'paycycle_out' and overtime > 0:
                res.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
                    'name': 'Regular Payout Overtime',
                    'number_of_days': overtime / avg_working_hour_per_day,
                    'number_of_hours': overtime,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            new_worked_days_lines = []
            for entry in res:
                entry_data = entry[2]  # Extracting the dictionary from the tuple
                if entry_data['work_entry_type_id'] == self.env.ref(
                        'hr_work_entry.work_entry_type_attendance').id:  # Checking if work_entry_type_id is 8
                    real_attendance_hour = entry_data['number_of_hours'] - overtime
                    entry_data['number_of_hours'] = real_attendance_hour  # Updating the number of hours to 10
                    entry_data[
                        'number_of_days'] = real_attendance_hour / avg_working_hour_per_day  # Updating the number of hours to 10
                new_worked_days_lines.append(entry)
                res = new_worked_days_lines
        return res


    def _create_banked_overtime_record(self):
        for rec in self:
            if rec.employee_id.overtime_method == 'banked_overtime':
                banked_store_overtime_obj = self.env['hr.attendance.overtime.store']
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                existing_overtime = self.env['hr.attendance.overtime.store'].search([("payment_pay_period", "=", rec.pay_cycle_period.id),('year','=',int(rec.date_from.year)),('employee_id', '=', rec.employee_id.id)])
                banked_overtime = rec.worked_days_line_ids.filtered(
                    lambda x: x.work_entry_type_id.code in ["BNK_OVERTIME"])
                current_hourly_rate = (rec.employee_id.contract_id.wage * 12) / (
                        rec.employee_id.contract_id.resource_calendar_id.full_time_required_hours * 52)
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
                if  not existing_overtime:
                    if banked_overtime.number_of_hours >0.0:
                        banked_store_overtime_obj.sudo().create({
                            'employee_id': rec.employee_id.id,
                            'date': rec.pay_cycle_period.start_date,
                            'payment_pay_period': rec.pay_cycle_period.id,
                            'duration_store': banked_overtime.number_of_hours,
                            'duration_remaining': banked_overtime.number_of_hours,
                            'overtime_rate': overtime_hour_rate,
                            'amount': banked_overtime.amount,
                        })
                else:
                    existing_overtime.write({
                        'duration_store': existing_overtime.duration_store+banked_overtime.number_of_hours,
                        'amount': existing_overtime.amount + banked_overtime.amount,
                    })

    def compute_sheet(self):
        input_type = self.env.ref('syncoria_can_overtime.input_ca_bank_overtime').id
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        for payslip in payslips:
            try:
                des_name = ","
                employee_id = payslip.employee_id
                overtime_pay_ids = payslip.env['hr.overtime.pay.request'].search(
                    [('employee_id', '=', employee_id.id)]).filtered(
                    lambda x: x.state == 'validate' and payslip.date_to >= x.date)
                calculate_overtime_pay = sum(overtime_pay_ids.mapped('overtime_pay'))

                if overtime_pay_ids and calculate_overtime_pay > 0.0:
                    payslip.input_line_ids.filtered(lambda x: x.input_type_id.id == input_type).unlink()
                    payslip.write({'input_line_ids': [(0, 0, {
                        'input_type_id': input_type,
                        'name': des_name.join(overtime_pay_ids.mapped('name')) or "",
                        'overtime_pay_req_ref': des_name.join(overtime_pay_ids.mapped('name')),
                        'amount': payslip._get_hourly_rate() * calculate_overtime_pay,
                    })]})

            except Exception as e:
                payslip.message_post(body=f"Overtime Pay Error:{e}")
        return super(InheritedHrPayslipOvertime,self).compute_sheet()


    # ============================================================================================================


    def compute_workdays_manual_input(self, manual_input_ids):
        super(InheritedHrPayslipOvertime, self).compute_workdays_manual_input(manual_input_ids)
        for rec in self:

            manual_input_line_id = manual_input_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            over_time_hour = manual_input_line_id.overtime_hours
            stat_over_time_hour = manual_input_line_id.stat_overtime_hours
            avg_working_hour_per_day = rec.contract_id.resource_calendar_id.hours_per_day
            worked_days_lines = []
            if over_time_hour > 0.0:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
                    'name': 'Overtime',
                    'number_of_days': over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': over_time_hour,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            if stat_over_time_hour > 0.0:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_stat_overtime_work_entry_type').id,
                    'name': 'Statutory Holidays Overtime',
                    'number_of_days': stat_over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': stat_over_time_hour,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))
            rec.worked_days_line_ids = worked_days_lines





    def _deduct_banked_overtime_amount(self):
        input_type = self.env.ref('syncoria_can_overtime.input_ca_bank_overtime').id
        other_input_line_overtime = self.input_line_ids.filtered(lambda x: x.input_type_id.id == input_type)
        if other_input_line_overtime:
            existing_overtime_pay_period_ids = self.env["hr.attendance.overtime.store"].search(
                [('employee_id', '=', self.employee_id.id),
                 ], order='date asc').filtered(lambda x: max(x.duration_store - x.duration_taken,0)>0.00)

            """
            Case 1: If taken amount is less than remaining amount then it's okk
            Case 2: If taken amount is greater than remaining amount then
                        a. Check remaining amount 
                        b. Taken amount will be remaining amount and deduct remaining amount from taken amount 
                        c. Then recursion call with that taken amount
            """
            overtime_req_obj = self.env['hr.overtime.pay.request']
            other_input_duration_taken = sum(overtime_req_obj.search(
                [('name', 'in', other_input_line_overtime.overtime_pay_req_ref.split(
                ',') if other_input_line_overtime.overtime_pay_req_ref else []), ('employee_id', '=', self.employee_id.id)], limit=1).mapped('overtime_pay'))
            other_input_amount_taken =other_input_line_overtime.amount

            for store_overtime in existing_overtime_pay_period_ids:

                if other_input_duration_taken > store_overtime.duration_remaining:
                    duration_need_to_deduct = store_overtime.duration_remaining
                    amount_need_to_deduct = store_overtime.remaining_amount
                    other_input_duration_taken -= duration_need_to_deduct
                    other_input_amount_taken -= amount_need_to_deduct

                    store_overtime.write({
                        'duration_taken':store_overtime.duration_taken+ duration_need_to_deduct,
                        'amount_taken': store_overtime.amount_taken + amount_need_to_deduct,
                        'payslip_ids': [Command.link(self.id)]
                    })
                else:
                    store_overtime.write({
                        'duration_taken': store_overtime.duration_taken+other_input_duration_taken,
                        'amount_taken': store_overtime.amount_taken+other_input_amount_taken,
                        'payslip_ids': [Command.link(self.id)]
                    })


            overtime_pay_req_ids = other_input_line_overtime.overtime_pay_req_ref.split(
                ',') if other_input_line_overtime.overtime_pay_req_ref else []
            for overtime_pay in overtime_pay_req_ids:
                ir_id = overtime_req_obj.search(
                    [('name', '=', overtime_pay), ('employee_id', '=', self.employee_id.id)], limit=1)
                if ir_id:
                    ir_id.write({
                        'state': 'paid'
                    })



    def action_payslip_done(self):
        res = super(InheritedHrPayslipOvertime, self).action_payslip_done()
        # for rec in self:
        #     rec._create_banked_overtime_record()
        return res

    def action_open_overtime(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Stored Overtime"),
            "res_model": "hr.attendance.overtime.store",
            "views": [[False, "tree"]],
            "context": {
                "create": 0
            },
            "domain": [('employee_id', '=', self.employee_id.id)]
        }


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _reconcile_payments(self, to_process, edit_mode=False):
        res = super()._reconcile_payments(to_process, edit_mode=edit_mode)
        for rec in self:
            payslip = rec.env['hr.payslip'].browse(self.env.context['hr_payroll_payment_register'])
            payslip._create_banked_overtime_record()
            payslip._deduct_banked_overtime_amount()

        return res

