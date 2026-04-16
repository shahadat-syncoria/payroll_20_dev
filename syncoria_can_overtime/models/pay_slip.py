import json
import logging
from datetime import timedelta, datetime, time

from dateutil.relativedelta import relativedelta
from ..helper.helper_functions import iso_weeks_in_year


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

    overtime_start_date = fields.Date(related="pay_cycle_period.overtime_start_date")
    overtime_end_date = fields.Date(related="pay_cycle_period.overtime_end_date")

    def _check_banked_overtime_constrain(self, banked_overtime_other_input):
        self.ensure_one()
        for rec in self:
            if rec.employee_id.overtime_method =='banked_overtime' and banked_overtime_other_input.amount > rec.total_stored_overtime_amount:
                raise ValidationError(_("Requested overtime greater than stored banked overtime amount!!"))


    # ========================================= New Overtime Concept =============================================
    def _get_hourly_rate(self):
        for rec in self:
            weeks_in_year = iso_weeks_in_year(rec.year)
            if not rec.version_id.is_hourly:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.fixed_wage_hourly_rate
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))
            else:
                overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                    'can_overtime_pay_percent', raise_if_not_found=False)
                current_hourly_rate = rec.version_id.hourly_wage
                overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))

            return overtime_hour_rate

    def _get_date_range_overtime(self):
        ot_from = self.overtime_start_date
        ot_to = self.overtime_end_date
        if ot_from and ot_to:
            return ot_from, ot_to
        else:
            return self.date_from,self.date_to

    def calculate_overtime(self):
        _logger.info(f"Payslip ID===>{self.id}")
        overtime_data = {}
        overtime_hours = 0
        weekly_overtime_hours = {}
        if self.version_id.overtime_threshold_selection == "fixed":
            full_week_hours = self.version_id.overtime_threshold
        if self.version_id.overtime_threshold_selection == "range":
            thresholds = self.version_id.overtime_threshold_id.line_ids
            full_week_hours = min(
                thresholds.mapped('start_threshold')
            ) if thresholds else 0.0
        # full_week_hours = self.version_id.overtime_threshold
        work_entry_source =self.version_id.work_entry_source
        employee = self.employee_id
        # Get the start and end date of the payslip
        slip_tz = pytz.timezone(self.version_id.resource_calendar_id.tz)
        utc = pytz.timezone('UTC')
        date_from, date_to = self._get_date_range_overtime()

        payslip_start_date = slip_tz.localize(datetime.combine(date_from, time.min)).astimezone(utc).replace(tzinfo=None)
        # payslip_start_date = datetime.combine(self.date_from, time.min)
        payslip_end_date = slip_tz.localize(datetime.combine(date_to, time.max)).astimezone(utc).replace(tzinfo=None)
        # payslip_end_date = datetime.combine(self.date_to, time.max)

        payslip_start_date =payslip_start_date.date()
        payslip_end_date = payslip_end_date.date()


        _logger.info(f"Start date:{payslip_start_date} and End Date: {payslip_end_date}")

        # Find the Monday of the start week and Sunday of the end week
        first_monday = payslip_start_date - timedelta(days=payslip_start_date.weekday())
        last_sunday = payslip_end_date

        _logger.info(f"First Monday:{first_monday} ")



        # Retrieve work entries for the payslip period
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', first_monday),
            ('date', '<=', last_sunday),
            ('state','in',['draft','validated'])
        ])

        # Initialize week tracking
        # current_week_start = datetime.combine(first_monday, time.min)
        current_week_start = slip_tz.localize(datetime.combine(first_monday, time.min)).astimezone(utc).replace(tzinfo=None)
        current_week_start = current_week_start.date()
        # current_week_end = datetime.combine((current_week_start + timedelta(days=4)), time.max)
        current_week_end = slip_tz.localize(datetime.combine((current_week_start + timedelta(days=4)), time.max)).astimezone(utc).replace(tzinfo=None)
        current_week_end =current_week_end.date()
        first_week = True
        if work_entry_source != "timesheet_hours":
            # Iterate through full weeks
            while current_week_start <= last_sunday:
                # Get work entries for the current week
                _logger.info(f"Week Start:{current_week_start} and current_week_end: {current_week_end} and IS first week:{first_week}")
                weekly_work_entries = work_entries.filtered(
                    lambda we: current_week_start <= we.date <= current_week_end
                )
                _logger.info(f"Weekly Work entries:{weekly_work_entries[-1].date if weekly_work_entries else None} and {weekly_work_entries[-1].date if weekly_work_entries else None}\n")

                # Calculate weekly hours
                weekly_hours = sum(
                    [we.duration for we in weekly_work_entries]
                )
                _logger.info(f"Weekly Hour:{weekly_hours}\n")


                if weekly_hours > full_week_hours:

                    # Handle partial weeks:
                    # If the pay period starts in the middle of the week
                    if payslip_start_date.weekday() != 0 and first_week:
                        _logger.info(f"First Partial Week===>")
                        first_partial_week_hours = sum(
                            [we.duration for we in work_entries.filtered(
                                lambda we: first_monday <= we.date < payslip_start_date
                            )]
                        )
                        _logger.info(f"First Partial Week Hour:{first_partial_week_hours} and Date Start: {first_monday} and End date:{payslip_start_date}")
                        if first_partial_week_hours > full_week_hours:
                            _logger.info(
                                f"first_partial_week_hours({first_partial_week_hours}) > full_week_hours{full_week_hours}")
                            first_partial_overtime_hours = first_partial_week_hours - full_week_hours
                            _logger.info(f"first_partial_overtime_hours({first_partial_overtime_hours})")
                            overtime = (weekly_hours - full_week_hours) - first_partial_overtime_hours
                            overtime_hours += overtime
                            weekly_overtime_hours[str(current_week_start)] = overtime
                            _logger.info(f"first_partial_overtime_hours({(weekly_hours - full_week_hours) - first_partial_overtime_hours})")

                    else:
                        overtime = weekly_hours - full_week_hours
                        overtime_hours += overtime
                        weekly_overtime_hours[str(current_week_start)] = overtime
                # Move to the next week
                current_week_start += timedelta(days=7)
                # current_week_start = datetime.combine(current_week_start, time.min)
                current_week_start = slip_tz.localize(datetime.combine(current_week_start, time.min)).astimezone(utc).replace(tzinfo=None)
                current_week_start = current_week_start.date()
                _logger.info(f"Next Week Start: {current_week_start})")
                current_week_end = current_week_start + timedelta(days=4)
                # current_week_end = datetime.combine(current_week_end, time.max)
                current_week_end = slip_tz.localize(datetime.combine(current_week_end, time.max)).astimezone(utc).replace(tzinfo=None)
                current_week_end = current_week_end.date()
                first_week = False
                _logger.info(f"Next Week Ends: {current_week_end})")
        else:
            while current_week_start <= last_sunday:
                # Get work entries for the current week
                _logger.info(f"Week Start:{current_week_start} and current_week_end: {current_week_end} and IS first week:{first_week}")

                # Calculate weekly hours
                working_hours = employee.get_timesheet_and_working_hours_for_employees(
                    current_week_start.__str__(), current_week_end.__str__()
                    ).get(self.employee_id.id, {})
                _logger.info(f"Weekly Hour:{working_hours}\n")
                weekly_hours = working_hours.get("worked_hours")

                if weekly_hours > full_week_hours:
                    # Handle partial weeks:
                    # If the pay period starts in the middle of the week
                    if payslip_start_date.weekday() != 0 and first_week:
                        _logger.info(f"First Partial Week===>")
                        first_partial_worked_hours = employee.get_timesheet_and_working_hours_for_employees(
                            first_monday.__str__(), payslip_start_date.__str__()
                        ).get(self.employee_id.id, {})
                        first_partial_week_hours =first_partial_worked_hours.get("worked_hours")
                        # first_partial_week_hours = sum(
                        #     [(we.date_stop - we.date_start).total_seconds() / 3600 for we in work_entries.filtered(
                        #         lambda we: we.date_start >= first_monday and we.date_stop < payslip_start_date
                        #     )]
                        # )
                        _logger.info(f"First Partial Week Hour:{first_partial_week_hours} and Date Start: {first_monday} and End date:{payslip_start_date}")
                        if first_partial_week_hours > full_week_hours:
                            _logger.info(
                                f"first_partial_week_hours({first_partial_week_hours}) > full_week_hours{full_week_hours}")
                            first_partial_overtime_hours = first_partial_week_hours - full_week_hours
                            _logger.info(f"first_partial_overtime_hours({first_partial_overtime_hours})")
                            overtime = (weekly_hours - full_week_hours) - first_partial_overtime_hours
                            overtime_hours += overtime
                            weekly_overtime_hours[str(current_week_start)] = overtime
                            _logger.info(f"first_partial_overtime_hours({(weekly_hours - full_week_hours) - first_partial_overtime_hours})")

                    else:
                        overtime = weekly_hours - full_week_hours
                        overtime_hours += overtime
                        weekly_overtime_hours[str(current_week_start)] = overtime

                # Move to the next week
                current_week_start += timedelta(days=7)
                current_week_start = slip_tz.localize(datetime.combine(current_week_start, time.min)).astimezone(utc).replace(tzinfo=None)
                _logger.info(f"Next Week Start: {current_week_start})")
                current_week_start = current_week_start.date()
                current_week_end = current_week_start + timedelta(days=4)
                current_week_end = slip_tz.localize(datetime.combine(current_week_end, time.max)).astimezone(utc).replace(tzinfo=None)
                current_week_end = current_week_end.date()
                first_week = False
                _logger.info(f"Next Week Ends: {current_week_end})")

        result = self.distribute_hours_from_thresholds(weekly_overtime_hours)


        if self.employee_id.overtime_threshold_selection == "fixed":
            overtime_data[self.employee_id.overtime_threshold] = overtime_hours
        if self.employee_id.overtime_threshold_selection == "range":
            overtime_data = result
        _logger.info(f"overtime_data")
        return overtime_data

    def distribute_hours_from_thresholds(self, weekly_overtime_hours):
        """
          Aggregates hours across all weeks into each threshold bucket.
          """
        thresholds = self.employee_id.overtime_threshold_id.line_ids.sorted('start_threshold')  # Ensure sorted by start
        summary = {}

        for threshold in thresholds:
            key = threshold.work_entry_id.code
            summary[key] = 0.0

        for date, total_hours in weekly_overtime_hours.items():
            remaining_hours = total_hours
            for threshold in thresholds:
                lower = threshold.start_threshold
                upper = threshold.end_threshold
                key = threshold.work_entry_id.code
                max_in_bucket = upper - lower

                if remaining_hours > max_in_bucket:
                    summary[key] += max_in_bucket
                    remaining_hours -= max_in_bucket
                else:
                    summary[key] += remaining_hours
                    break  # Done allocating hours

        return summary

    def _get_new_worked_days_lines(self):

        res = super()._get_new_worked_days_lines()

        if self.employee_id.overtime_method in ['banked_overtime', 'paycycle_out'] and self.pay_cycle_period:
            overtime_data = self.calculate_overtime()  # e.g. {'threshold 40': 1.25, 'threshold 41.25': 6.75}
            avg_working_hour_per_day = self.version_id.resource_calendar_id.hours_per_day

            for threshold_label, overtime_hours in overtime_data.items():
                if overtime_hours <= 0:
                    continue


                work_entry_type = self.env['hr.work.entry.type'].search(
                    [('code', '=', threshold_label)],
                    limit=1
                )

                if work_entry_type:
                    work_entry_type_id = work_entry_type.id
                else:
                    work_entry_type_id = (
                        self.env.ref('syncoria_can_overtime.sync_banked_overtime_work_entry_type').id
                        if self.employee_id.overtime_method == 'banked_overtime'
                        else self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id
                    )

                res.append((0, 0, {
                    'work_entry_type_id': work_entry_type_id,
                    'name': f'Overtime ({threshold_label})',
                    'number_of_days': overtime_hours / avg_working_hour_per_day,
                    'number_of_hours': overtime_hours,
                }))

            # Deduct total overtime from attendance/timesheet entries
            total_overtime = sum(overtime_data.values())
            new_worked_days_lines = []
            for entry in res:
                entry_data = entry[2]
                if entry_data['work_entry_type_id'] in [
                    self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                    self.env.ref('syncoria_payroll_timesheet.sync_work_type_timesheet').id
                ]:
                    real_attendance_hour = entry_data['number_of_hours'] - total_overtime
                    entry_data['number_of_hours'] = real_attendance_hour
                    entry_data['number_of_days'] = real_attendance_hour / avg_working_hour_per_day
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
                current_hourly_rate = rec.fixed_wage_hourly_rate
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
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'validated'])
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
            avg_working_hour_per_day = rec.version_id.resource_calendar_id.hours_per_day
            worked_days_lines = []
            input_line = []
            overtime_wet = self.env.ref(
                'syncoria_can_overtime.sync_overtime_work_entry_type',
                raise_if_not_found=False
            )
            stat_overtime_wet = self.env.ref(
                'syncoria_can_overtime.sync_stat_overtime_work_entry_type',
                raise_if_not_found=False
            )
            overtime_exists = any(
                line.work_entry_type_id == overtime_wet
                for line in rec.worked_days_line_ids
            )
            sat_overtime_exists = any(
                line.work_entry_type_id == stat_overtime_wet
                for line in rec.worked_days_line_ids
            )
            if over_time_hour > 0.0 and not overtime_exists:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
                    'name': 'Canada Overtime hours',
                    'number_of_days': over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': over_time_hour,
                    # 'amount': timesheet_hours*payslip.version_id.hourly_wage

                }))
            if stat_over_time_hour > 0.0 and not sat_overtime_exists:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_stat_overtime_work_entry_type').id,
                    'name': 'Statutory Holidays Overtime',
                    'number_of_days': stat_over_time_hour / avg_working_hour_per_day,
                    'number_of_hours': stat_over_time_hour,
                    # 'amount': timesheet_hours*payslip.version_id.hourly_wage

                }))
            rec.worked_days_line_ids = worked_days_lines
            rec.input_line_ids = input_line





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
            if self.env.context.get('hr_payroll_payment_register'):
                for vals in to_process:
                    payslip = vals['to_reconcile'].move_id.payslip_ids
                # payslip = rec.env['hr.payslip'].browse(self.env.context['hr_payroll_payment_register'])
                    payslip._create_banked_overtime_record()
                    payslip._deduct_banked_overtime_amount()

        return res

