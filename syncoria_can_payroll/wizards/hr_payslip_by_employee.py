from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class SyncoriaHrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'




    def _get_employees(self):
        res = super(SyncoriaHrPayslipEmployees,self)._get_employees()
        context = self.env.context
        if 'active_model' in context and context.get('active_model') == 'hr.payslip.run':
            hr_payslip_run= self.env['hr.payslip.run'].browse(context.get('active_id'))
            contract_domain = [('contract_ids.state', 'in', ('open',)),
                               ('company_id', '=', self.env.company.id),
                               ('contract_ids.salary_pay_cycle','in',hr_payslip_run.pay_cycle.ids)]
            employees = self.env['hr.employee'].search(contract_domain)
            return employees

        return res
    @api.onchange('employee_ids')
    def _onchange_employee_domain(self):
        for rec in self:
            context = rec.env.context
            hr_payslip_run = rec.env['hr.payslip.run'].browse(context.get('active_id'))
            employee_domains =  rec.env['hr.employee'].search( [('contract_ids.state', 'in', ('open',)),
                               ('company_id', '=', rec.env.company.id),
                               ('contract_ids.salary_pay_cycle','in',hr_payslip_run.pay_cycle.ids)]).ids
            return {'domain': {'employee_ids': [('id', 'in', employee_domains)]}}


class SyncoriaHrEmployeeManualWizard(models.TransientModel):
    _name = "hr.payslip.employee.manual.wizard"
    _description = "HR Employee Manual Wizard"
    @api.model
    def _get_default_attendance_hours(self,hr_payslip_run,employee_id):
        if not employee_id.contract_id.is_hourly:
            return (hr_payslip_run.date_end - hr_payslip_run.date_start).days *employee_id.contract_id.standard_calendar_id.hours_per_day
        else:
            return 0.0

    def _get_employees(self):
        context = self.env.context
        if 'active_model' in context and context.get('active_model') == 'hr.payslip.run':
            hr_payslip_run = self.env['hr.payslip.run'].browse(context.get('active_id'))
            contract_domain = [('contract_ids.state', 'in', ('open',)),
                               ('company_id', '=', self.env.company.id),
                               ('contract_ids.salary_pay_cycle', 'in', hr_payslip_run.pay_cycle.ids)]
            # employees = self.env['hr.employee'].search(contract_domain)

            rec = []
            for employee in self.env['hr.employee'].search(contract_domain):
                rec.append((0,0,{
                    "employee_id": employee.id,
                    "attendance_hours": self._get_default_attendance_hours(hr_payslip_run,employee),
                    "ytd_vac_pay_amount" : employee.ytd_vac_pay_amount
                }))
            # return [(0,0,{"employee_id": employee.id}) for employee in self.env['hr.employee'].search(contract_domain)]
            return rec

    manual_input_ids = fields.One2many("hr.employee.manual.input.line", 'manual_input_wizard_id', default=lambda self: self._get_employees())

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            if contract.work_entry_source != 'calendar':
                continue
            calendar_start = pytz.utc.localize(
                datetime.combine(max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(
                datetime.combine(min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals_batch(calendar_start, calendar_end)[
                          False] - work_entries._to_intervals()
            if outside:
                time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in outside._items]])
                raise UserError(
                    _("Some part of %s's calendar is not covered by any work entry. Please complete the schedule. Time intervals to look for:%s") % (
                    contract.employee_id.name, time_intervals_str))

    def _filter_contracts(self, contracts):
        # Could be overriden to avoid having 2 'end of the year bonus' payslips, etc.
        return contracts

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))

            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.manual_input_ids.with_context(active_test=False).employee_id
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        # Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
        ).filtered(lambda c: c.active)
        contracts.generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        # if (self.structure_id.type_id.default_struct_id == self.structure_id):
        #     work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
        #     if work_entries._check_if_error():
        #         work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        #
        #         for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
        #             work_entries_by_contract[work_entry.contract_id] |= work_entry
        #
        #         for contract, work_entries in work_entries_by_contract.items():
        #             conflicts = work_entries._to_intervals()
        #             time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
        #         return {
        #             'type': 'ir.actions.client',
        #             'tag': 'display_notification',
        #             'params': {
        #                 'title': _('Some work entries could not be validated.'),
        #                 'message': _('Time intervals to look for:%s', time_intervals_str),
        #                 'sticky': False,
        #             }
        #         }

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        for rec in payslips:
            rec._compute_name()
            rec.compute_workdays_manual_input(self.manual_input_ids)
            rec.compute_sheet()
        # payslips._compute_name()
        # payslips.compute_workdays_manual_input(self.manual_input_ids)
        # payslips.compute_sheet()
        payslip_run.state = 'verify'

        return success_result

class SyncoriaEmployeeManualInputLine(models.TransientModel):
    _name = "hr.employee.manual.input.line"
    _description = "HR Employee Manual Input Line"

    manual_input_wizard_id= fields.Many2one("hr.payslip.employee.manual.wizard")
    create_draft_id= fields.Many2one("hr.payslip.create.draft.wizard")
    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    slip_id = fields.Many2one("hr.payslip", string="Slip_id")

    attendance_hours = fields.Float(string="Attendance Number of Hours")
    overtime_hours = fields.Float(string="Overtime Number of Hours")
    stat_overtime_hours = fields.Float(string="Statutory Overtime Number of Hours")

    payout_vacation_pay_paycycle = fields.Boolean("Payout Vacation Amount Per Pay Cycle", default=False,
                                                  groups='hr.group_hr_user')
    #======= have to make it related with employee_id================
    ytd_vac_pay_amount = fields.Float("Remaining Vacation Pay")

    vac_pay = fields.Float("Vacation Pay Amount")
    commission = fields.Float("Commission Amount")
    bonus = fields.Float("Bonus Amount")
    retro = fields.Float("Retro Amount")


    @api.constrains("vac_pay")
    def _check_vac_pay(self):
        for rec in self:
            if rec.ytd_vac_pay_amount < rec.vac_pay:
                raise UserError("Vacation pay amount cannot be greater then Remaining Vacation Pay.")


