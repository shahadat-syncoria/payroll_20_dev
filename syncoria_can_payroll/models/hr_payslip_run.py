import calendar
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import ast
from odoo import api, fields, models
from ..helper.helper_functions import year_selection
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


class PayrollHrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    pay_cycle = fields.Many2one('paycycle.config',store=True)
    pay_cycle_period = fields.Many2one('paycycle.period' , store=True)
    pay_cycle_period_ids_domain = fields.Json(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)

    pay_cycle_year = fields.Selection(
        year_selection,
        string="Year",
        default=str(fields.Date.today().year), readonly=True)

    is_manual_input = fields.Boolean(compute='_compute_is_manual_input')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('pay_cycle_period'):
                period = self.env['paycycle.period'].browse(vals['pay_cycle_period'])
                vals['name'] = period.name
        return super().create(vals_list)

    def _compute_is_manual_input(self):
        with_user = self.env['ir.config_parameter'].sudo()
        attendance_manual = with_user.get_bool('syncoria_can_payroll.attendance_manual_input')
        for payslip in self:
            payslip.is_manual_input = attendance_manual

    @api.depends('pay_cycle','pay_cycle_year')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle:
                pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_year_slab_ids.filtered(
                    lambda x: x.year == str(rec.pay_cycle_year)).paycycle_period_ids.ids
                # pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_ids.filtered(
                #     lambda x: x.paycycle_config_id.id == rec.pay_cycle.id and x.paycycle_year_slab_id.year == str(rec.year)).ids
                rec.pay_cycle_period_ids_domain = pay_cycle_period_ids_domain

    @api.onchange('pay_cycle_period')
    def _onchange_pay_cycle_period(self):
        for rec in self:
            if rec.pay_cycle_period:
                rec.update({
                    'name': rec.pay_cycle_period.name + f'-{rec.pay_cycle_year}',
                    'date_start': rec.pay_cycle_period.start_date,
                    'date_end': rec.pay_cycle_period.end_date
                })
    def action_draft_entry_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Draft Payslips',
            'res_model': 'hr.payslip.create.draft.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_active_id': self.id,  # Pass the active payslip run's ID
                'default_active_model': self._name,
                'dialog_size': 'large'
            },

        }


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
                    'state': '03_paid'
                })

    def action_validate(self):
        # Odoo 20: hr.payslip.run.action_close was replaced by action_validate
        res = super(PayrollHrPayslipRun, self).action_validate()
        for rec in self:
            rec.next_batch_create()
        return res

    # ================ Schedular mail notification ===============

    def send_reminder_mail(self):
        try:
            with_user = self.env['ir.config_parameter'].sudo()
            reminder_days = with_user.get_str('syncoria_can_payroll.reminder_days_before_payroll')
            if reminder_days:
                email_partner_ids = ast.literal_eval(with_user.get_str('syncoria_can_payroll.reminder_recipient_ids'))
                email_partner_obj_ids = self.env['res.partner'].browse(email_partner_ids)
                email_ids = ','.join([i.email for i in email_partner_obj_ids])
                payslip_date_acc_reminder = datetime.now() + timedelta(days=int(reminder_days))
                draft_payslip_ids = self.search(
                    [('date_end', '=', payslip_date_acc_reminder.date()), ('state', 'in', ['00_draft', '01_ready'])])
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

    def action_payslip_refresh(self):
        for x in self.slip_ids:
            print(x)
            x._onchange_pay_cycle_period()
            x.compute_sheet()


    # Odoo 20: the pay run employee selection works on hr.employee (hr_payroll.action_view_employee_tree)
    # and versions are resolved by hr.payslip.run._get_valid_versions(). The pay cycle filter is injected
    # through _get_valid_versions_domain_payrun (context key or the pay run's own pay cycle).
    def action_payroll_hr_version_list_view_payrun_cus(self, date_start=None, date_end=None, structure_id=None,
                                                       company_id=None, pay_cycle=None, employee_type_ids=None):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_payroll.action_view_employee_tree')

        pay_cycle_id = pay_cycle.get("id") if isinstance(pay_cycle, dict) else pay_cycle
        payrun = self.with_context(payrun_pay_cycle_id=pay_cycle_id or False)
        date_start = fields.Date.from_string(date_start) if date_start else self.date_start
        date_end = fields.Date.from_string(date_end) if date_end else self.date_end
        valid_versions = payrun._get_valid_versions(date_start, date_end, structure_id, company_id, employee_type_ids)

        structure = structure_id if structure_id else (self.structure_id.id if self.structure_id else False)
        payslip_domain = Domain.AND([
            Domain('version_id', 'in', valid_versions.ids),
            Domain('date_from', '=', date_start),
            Domain('date_to', '=', date_end),
            Domain('struct_id', '=', structure),
            Domain('state', '!=', 'cancel'),
            Domain('pay_cycle', '=', pay_cycle_id or False)
        ])
        existing_versions = self.env['hr.payslip'].search(payslip_domain).version_id
        filtered_versions = valid_versions - existing_versions - self.version_ids
        action['domain'] = [("id", "in", filtered_versions.employee_id.ids)]
        return action

    def _get_valid_versions_domain_payrun(self, date_start=None, date_end=None, structure_id=None, company_id=None,
                                          employee_type_ids=None):
        version_domain = super()._get_valid_versions_domain_payrun(
            date_start, date_end, structure_id, company_id, employee_type_ids)
        pay_cycle_id = self.env.context.get('payrun_pay_cycle_id')
        if not pay_cycle_id and len(self) == 1:
            pay_cycle_id = self.pay_cycle.id
        if pay_cycle_id:
            version_domain &= Domain([('salary_pay_cycle', '=', pay_cycle_id)])
        return version_domain

    def _generate_payslips(self):
        # Odoo 20: generate_payslips(version_ids, employee_ids) was replaced by _generate_payslips()
        self.ensure_one()
        if self.slip_ids:
            self.slip_ids.write({
                "pay_cycle_period": self.pay_cycle_period.id,
            })
        return super(PayrollHrPayslipRun, self)._generate_payslips()

    def action_open_manual_wizard_from_list(self, employee_ids):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'syncoria_can_payroll.action_hr_employee_manual_input_wiz'
        )
        action['context'] = {
            'selected_employee_ids': employee_ids,


        }

        return action


