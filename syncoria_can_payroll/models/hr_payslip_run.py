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

    pay_cycle = fields.Many2one('paycycle.config')
    pay_cycle_period = fields.Many2one('paycycle.period' , store=True)
    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)

    pay_cycle_year = fields.Selection(
        year_selection,
        string="Year",
        default=str(fields.Date.today().year), readonly=True)

    is_manual_input = fields.Boolean(compute='_compute_is_manual_input')

    @api.onchange('pay_cycle')
    def _onchage_schedule_pay(self):
        self.ensure_one()
        if self.pay_cycle.pay_cycle == '12':
            self.schedule_pay = 'monthly'

        elif self.pay_cycle.pay_cycle == '24':
            self.schedule_pay = 'semi-monthly'

        elif self.pay_cycle.pay_cycle == '26':
            self.schedule_pay = 'bi-weekly'
        elif self.pay_cycle.pay_cycle == '52':
            self.schedule_pay = 'weekly'


    def _compute_is_manual_input(self):
        with_user = self.env['ir.config_parameter'].sudo()
        attendance_manual = with_user.get_param('syncoria_can_payroll.attendance_manual_input')
        for payslip in self:
            payslip.is_manual_input = True if attendance_manual == 'True' else False

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
                    [('date_end', '=', payslip_date_acc_reminder.date()), ('state', 'in', ['draft', 'validated'])])
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


    #  For Odoo 19 Selecting domain from js
    def action_payroll_hr_version_list_view_payrun_cus(self, date_start=None, date_end=None, structure_id=None,
                                                   company_id=None, pay_cycle=None):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_payroll.action_payroll_hr_version_list_view_payrun')

        valid_version_ids = self._get_valid_version_ids(
            fields.Date.from_string(date_start),
            fields.Date.from_string(date_end),
            structure_id,
            company_id,
            None,
            pay_cycle

        )

        payslip_domain = Domain.AND([
            Domain('version_id', 'in', valid_version_ids),
            Domain('date_from', '=', fields.Date.from_string(date_start) if date_start else self.date_start),
            Domain('date_to', '=', fields.Date.from_string(date_end) if date_end else self.date_end),
            Domain('struct_id', '=',
                   structure_id if structure_id else (self.structure_id.id if self.structure_id else False)),
            Domain('state', '!=', 'cancel'),
            Domain('pay_cycle', '=', pay_cycle.get("id") if pay_cycle else False)
        ])
        existing_version_ids = self.env['hr.payslip'].search(payslip_domain).version_id.ids
        filtered_version_ids = set(valid_version_ids) - set(existing_version_ids)
        action['domain'] = [("id", "in", list(filtered_version_ids))]
        return action


    def _get_valid_version_ids(self, date_start=None, date_end=None, structure_id=None, company_id=None, employee_ids=None,pay_cycle=None):
        super()._get_valid_version_ids(date_start=None, date_end=None, structure_id=None, company_id=None, employee_ids=None)

        date_start = date_start or self.date_start
        date_end = date_end or self.date_end
        structure = self.env["hr.payroll.structure"].browse(structure_id) if structure_id else self.structure_id

        pay_cycle = pay_cycle or self.pay_cycle
        company = company_id or self.company_id.id
        version_domain = Domain([
            ('company_id', '=', company),
            ('employee_id', '!=', False),
            ('contract_date_start', '<=', date_end),
            '|',
                ('contract_date_end', '=', False),
                ('contract_date_end', '>=', date_start),
            ('date_version', '<=', date_end),
        ])
        if structure:
            version_domain &= Domain([('structure_type_id', '=', structure.type_id.id)])
        if employee_ids:
            version_domain &= Domain([('employee_id', 'in', employee_ids)])
        if pay_cycle:
            version_domain &= Domain([('salary_pay_cycle', '=', pay_cycle.get("id"))])
        all_versions = self.env['hr.version']._read_group(
            domain=version_domain,
            groupby=['employee_id', 'date_version:day'],
            order="date_version:day DESC",
            aggregates=['id:recordset'],
        )
        all_employee_versions = defaultdict(list)
        for employee, _, version in all_versions:
            all_employee_versions[employee] += [*version]
        valid_versions = self.env["hr.version"]
        for employee_versions in all_employee_versions.values():
            employee_valid_versions = self.env["hr.version"]
            for i in range(len(employee_versions)):
                version = employee_versions[i]
                if version.date_version <= date_start or employee_versions[-1] == version:
                    # End case: The first version in contract before the pay run start or the last version of the list
                    employee_valid_versions |= version
                    break
                if employee_valid_versions:
                    # Version already added => new contract?
                    if (employee_valid_versions[-1].contract_date_start > version.contract_date_start
                        and (version.contract_date_start >= version.date_version
                            or version.contract_date_start > employee_versions[i + 1].contract_date_start)):
                        # Take only the first version of the new contract founded
                        employee_valid_versions |= version
                elif version.contract_date_start >= version.date_version or version.contract_date_start > employee_versions[i + 1].contract_date_start:
                    # Take only the first version of the first contract founded
                    employee_valid_versions |= version
            valid_versions |= employee_valid_versions
        return valid_versions.ids



    def generate_payslips(self, version_ids=None, employee_ids=None):
        if self.slip_ids:
            self.slip_ids.write({
                "pay_cycle_period": self.pay_cycle_period,
            })
        res = super(PayrollHrPayslipRun, self).generate_payslips(version_ids=version_ids, employee_ids=employee_ids)



        return 1

    def action_open_manual_wizard_from_list(self, employee_ids):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'syncoria_can_payroll.action_hr_employee_manual_input_wiz'
        )
        action['context'] = {
            'selected_employee_ids': employee_ids,


        }

        return action


