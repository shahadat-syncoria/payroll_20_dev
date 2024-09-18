from odoo import fields, models, api, _
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import UserError


def _month_selection(self):
    """
    Never change this helper function !!!!!!!!!
    It has impact in database .
    """
    month = 0
    month_list = []
    while month != 36:
        month_list.append((str(month), str(month)))
        month += 1
    return month_list


class VacationPayslip(models.Model):
    _inherit = 'hr.employee'

    vacation_pay_taken = fields.Float("Vacation Pay Taken", default= 0.0, compute='get_vacation_pay', groups='hr.group_hr_user')
    vacation_pay_allocation_start = fields.Selection(
        _month_selection,
        default='0',
        required=True,
        string="Allocation Start", help="0 means immediate start", groups='hr.group_hr_user')

    allocated_vacation_leave = fields.Float("Allocated Vacation Leave", default=0.0,tracking=True,groups='hr_holidays.group_hr_holidays_manager',readonly=True,
                                            compute='_get_allocated_vacation_pay')
    previous_allocated_vacation_leave = fields.Float("Previous Allocated Vacation Leave", default=0.0, tracking=True,
                                            groups='hr_holidays.group_hr_holidays_manager' )
    vacation_leave_write_date = fields.Datetime(string="Last Updated at", groups='hr.group_hr_user')

    # =================================================== Cash Wise store Vacation Pay(Earned Vacation Pay) ========================================
    ytd_vac_pay_amount = fields.Float("Remaining Vacation Pay Amount", default=0.0,compute="_compute_vac_pay_amount",store=True)
    ytd_vac_pay_amount_erp = fields.Float("Vacation Pay Amount ERP", default=0.0)
    previous_vac_pay_amount = fields.Float("Previous Vacation Pay Amount", default=0.0)
    vac_pay_amount_taken = fields.Float("Vacation Pay Amount Taken", default=0.0,store=True,readonly=True)

    allocated_vac_leave = fields.Float("Allocated Vacation Leave Per year",store=True, default=0.0,compute='_get_employee_allocated_leave')
    allocated_vac_percentage = fields.Float("Allocated Vacation Percentage",store=True, default=0.0,compute='_get_employee_allocated_leave')

    is_adjust_vacation_pay_leave = fields.Boolean("Adjust Vacation Pay With Unpaid Leaves",default=False)
    payout_vacation_pay_paycycle = fields.Boolean("Payout Vacation Amount Per Pay Cycle",default=False)
    is_vacation_pay_adjust_negative = fields.Boolean(" Vacation pay amount be negative",default=False)





    @api.constrains("is_adjust_vacation_pay_leave","payout_vacation_pay_paycycle")
    def _constrain_on_vacation_pay_bool(self):
        for rec in self:
            if rec.is_adjust_vacation_pay_leave and rec.payout_vacation_pay_paycycle:
                raise UserError("Adjust Vacation Pay With Unpaid Leaves and Payout Vacation Amount Per Pay Cycle Both Can't Enable Same Time!!")

    @api.onchange("is_adjust_vacation_pay_leave")
    def _onchange_is_adjust_vacation_pay_leave(self):
        for rec in self:
            if not rec.is_adjust_vacation_pay_leave:
                rec.is_vacation_pay_adjust_negative = False

    @api.depends("ytd_vac_pay_amount_erp", "previous_vac_pay_amount")
    def _compute_vac_pay_amount(self):
        for rec in self:
            rec.ytd_vac_pay_amount = (rec.ytd_vac_pay_amount_erp + rec.previous_vac_pay_amount) - rec.vac_pay_amount_taken

    def _get_vac_pay_slip_ids(self):
        """
            This is helper function to get YTD paid payslips compute line ids
        """
        payslip = self.slip_ids.filtered(
            lambda x: x.state == 'paid' )

        return payslip

    def update_vac_pay_amount_erp(self):
        for rec in self:
            payslips = rec._get_vac_pay_slip_ids()
            rec.ytd_vac_pay_amount_erp = sum(payslips.mapped('vac_pay_earned_amount'))
            rec.vac_pay_amount_taken = sum(payslips.mapped('vac_pay_earned_taken'))

    def _get_employee_allocated_leave(self):
        for rec in self:
            allocated_leave = 0
            allocated_percentage = 0
            if rec.sync_first_contract_date:
                today_month_from_first_contract = relativedelta(datetime.today().date(), rec.sync_first_contract_date)
                if today_month_from_first_contract.months >= int(rec.vacation_pay_allocation_start):
                    vacation_slab_id = rec.env['hr.vacation.slab'].search(
                        [
                            ('start_year', '<=', today_month_from_first_contract.years),
                            ('end_year', '>=', today_month_from_first_contract.years)
                        ], limit=1
                    )
                    allocated_leave = vacation_slab_id.allocated_leave
                    allocated_percentage = vacation_slab_id.leave_percentage

            rec.allocated_vac_leave = allocated_leave
            rec.allocated_vac_percentage = allocated_percentage




    @api.constrains('previous_allocated_vacation_leave')
    def _constraint_previous_allocated_leave(self):
        for rec in self:
            if rec.previous_allocated_vacation_leave < 0.0:
                raise UserError("Previous Allocation can not be negative!")

    def _get_vacation_pay_calculation(self):
        taken_vacation_leave = sum(self.env['hr.vacation.pay'].search([('employee_id', '=', self.id)]).filtered(
            lambda x: x.state == 'paid').mapped('duration'))
        return taken_vacation_leave

    def get_vacation_pay(self):
        if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type')=='time_wise':
            self.vacation_pay_taken = self._get_vacation_pay_calculation()
        else:
            self.vacation_pay_taken = 0.0

    def get_employee_years(self):
        for employee in self:
            start_date = employee.sync_first_contract_date  # Replace 'date_of_joining' with the actual field name in your model
            if start_date:
                today = datetime.now().date()
                years_difference = today.year - start_date.year

                # Checking if today's date is before the anniversary of the start date
                if today.month < start_date.month or (today.month == start_date.month and today.day < start_date.day):
                    years_difference -= 1

                return years_difference



    def _calculated_vacation_pay_allocated(self):
        for rec in self:
            if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type')=='time_wise':
                today_date = datetime.today().date()

                def _is_leap_year():
                    return 366 if calendar.isleap(today_date.year) else 365

                rec.allocated_vacation_leave = 0.0
                if rec.sync_first_contract_date:
                    today_month_from_first_contract = relativedelta(datetime.today().date(), rec.sync_first_contract_date)
                    if today_month_from_first_contract.months >= int(rec.vacation_pay_allocation_start):
                        vacation_slab_id = rec.env['hr.vacation.slab'].search(
                            [
                                ('start_year', '<=', today_month_from_first_contract.years),
                                ('end_year', '>=', today_month_from_first_contract.years)
                            ], limit=1
                        )
                        start_date = (
                                         rec.sync_first_contract_date if rec.sync_first_contract_date.year == today_date.year else datetime(
                                             today_date.year, 1, 1).date())
                        rec.allocated_vacation_leave += (((vacation_slab_id.allocated_leave / _is_leap_year()) * (
                                (today_date-timedelta(days=1)) - start_date).days + rec.previous_allocated_vacation_leave) - rec._get_vacation_pay_calculation())
                        if rec.allocated_vacation_leave < 0.0:
                            rec.allocated_vacation_leave = 0.0
                else:
                    rec.allocated_vacation_leave = 0.0
    def _get_allocated_vacation_pay(self):

        self._calculated_vacation_pay_allocated()
        self.vacation_leave_write_date = datetime.now()

