import calendar
from datetime import datetime, timedelta
import logging
import ast
from odoo import api, fields, models
from ..helper.helper_functions import year_selection

_logger = logging.getLogger(__name__)


class PayrollHrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    pay_cycle = fields.Many2one('paycycle.config')
    pay_cycle_period = fields.Many2one('paycycle.period')
    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)

    pay_cycle_year = fields.Selection(
        year_selection,
        string="Year",
        default=str(fields.Date.today().year), readonly=True)

    is_manual_input = fields.Boolean(compute='_compute_is_manual_input')


    def _compute_is_manual_input(self):
        with_user = self.env['ir.config_parameter'].sudo()
        attendance_manual = with_user.get_param('syncoria_can_payroll.attendance_manual_input')
        for payslip in self:
            payslip.is_manual_input = True if attendance_manual == 'True' else False

    @api.depends('pay_cycle')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            if rec.pay_cycle_period.paycycle_config_id != rec.pay_cycle:
                rec.pay_cycle_period = None
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle:
                rec.pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_ids.filtered(
                    lambda x: x.paycycle_config_id.id == rec.pay_cycle.id).ids

    @api.onchange('pay_cycle_period')
    def _onchange_pay_cycle_period(self):
        for rec in self:
            if rec.pay_cycle_period:
                rec.update({
                    'name': rec.pay_cycle_period.name + f'-{fields.Date.today().year}',
                    'date_start': rec.pay_cycle_period.start_date,
                    'date_end': rec.pay_cycle_period.end_date
                })

    def get_next_calendar_date(self, current_date):
        # Get the current date

        # Increment the current date by one day
        next_date = current_date + timedelta(days=1)

        # Check if the next date is valid
        while not calendar.isleap(next_date.year) and next_date.day == 29 and next_date.month == 2:
            next_date += timedelta(days=1)

        # Return the next calendar date
        return next_date

    def next_batch_create(self):
        try:
            next_pay_period_date = self.get_next_calendar_date(self.pay_cycle_period.end_date)
            next_pay_cycle_period = self.pay_cycle_period.search(
                [('start_date', '=', next_pay_period_date), ('paycycle_config_id', '=', self.pay_cycle.id)], limit=1)

            if next_pay_cycle_period:
                exist_data = self.search(
                    [('pay_cycle_year', '=', str(fields.Date.today().year)),
                     ('pay_cycle_period', '=', next_pay_cycle_period.id)], limit=1)
                if not exist_data:
                    data = {
                        'name': "Auto--->" + next_pay_cycle_period.name + f'-{fields.Date.today().year}',
                        'date_start': next_pay_cycle_period.start_date,
                        'date_end': next_pay_cycle_period.end_date,
                        'pay_cycle': self.pay_cycle.id,
                        'pay_cycle_period': next_pay_cycle_period.id,
                        'company_id': self.env.company.id,
                    }
                    try:
                        self.create(data)
                    except:
                        pass
                else:
                    self.message_post(body=f"Next batch: {exist_data.name} already exist")
        except Exception as e:
            _logger.warning(str(e))

    def _check_paid_status(self):
        for rec in self:
            if all(slip.state in ['paid'] for slip in rec.mapped('slip_ids')):
                rec.write({
                    'state': 'paid'
                })

    def action_close(self):
        super(PayrollHrPayslipRun, self).action_close()
        for rec in self:
            rec.next_batch_create()

    # ================ Schedular mail notification ===============

    def send_reminder_mail(self):
        try:
            with_user = self.env['ir.config_parameter'].sudo()
            reminder_days = with_user.get_param('syncoria_can_payroll.reminder_days_before_payroll')
            if reminder_days:
                email_partner_ids = ast.literal_eval(with_user.get_param('syncoria_can_payroll.reminder_recipient_ids'))
                email_partner_obj_ids = self.env['res.partner'].browse(email_partner_ids)
                email_ids = ','.join([i.email for i in email_partner_obj_ids])
                payslip_date_acc_reminder = datetime.now() + timedelta(days=int(reminder_days))
                draft_payslip_ids = self.search(
                    [('date_end', '=', payslip_date_acc_reminder.date()), ('state', 'in', ['draft', 'verify'])])
                mail_template = self.env.ref('syncoria_can_payroll.email_template_payroll_reminder')
                for payslip in draft_payslip_ids:
                    mail_template.send_mail(
                        payslip.id,

                        email_values={
                            'email_to': email_ids
                        },
                        force_send=True,

                    )
        except Exception as e:
            _logger.warning(f"Email Not send.\n Exception{e}")
