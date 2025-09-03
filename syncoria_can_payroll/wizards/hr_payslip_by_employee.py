# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date
from dateutil.relativedelta import relativedelta


class SyncoriaHrPayslipEmployees(models.TransientModel):
    _inherit = "hr.payslip.employees"

    # New One2many field to manage employees with checkbox
    line_ids = fields.One2many(
        "hr.payslip.employees.line",
        "wizard_id",
        string="Employees"
    )

    # Override default_get → populate line_ids from _get_employees()
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        employees = self._get_employees()
        if employees:
            res["line_ids"] = [(0, 0, {"employee_id": emp.id}) for emp in employees]
        return res

    @api.onchange('department_id', 'job_id', 'structure_type_id')
    def _onchange_filters(self):
        """Recompute line_ids when filters change (like employee_ids used to)."""
        for wizard in self:
            domain = wizard.get_employees_domain()
            employees = self.env['hr.employee'].search(domain)
            wizard.line_ids = [(5, 0, 0)]  # clear existing
            wizard.line_ids = [(0, 0, {"employee_id": emp.id}) for emp in employees]

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get("active_id"):
            from_date = fields.Date.to_date(self.env.context.get("default_date_start"))
            end_date = fields.Date.to_date(self.env.context.get("default_date_end"))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime("%B %Y")
            else:
                batch_name = _("From %(from_date)s to %(end_date)s",
                               from_date=format_date(self.env, from_date),
                               end_date=format_date(self.env, end_date))
            payslip_run = self.env["hr.payslip.run"].create({
                "name": batch_name,
                "date_start": from_date,
                "date_end": end_date,
            })
        else:
            payslip_run = self.env["hr.payslip.run"].browse(self.env.context.get("active_id"))

        # Get employees from line_ids excluding removed ones
        employees = self.line_ids.filtered(lambda l: not l.is_remove).mapped("employee_id")

        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        # Prevent duplicate payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.run",
            "views": [[False, "form"]],
            "res_id": payslip_run.id,
        }
        if not employees:
            payslip_run.slip_ids.write({"state": "verify"})
            payslip_run.state = "verify"
            return success_result

        Payslip = self.env["hr.payslip"]

        contracts = employees._get_contracts(
            payslip_run.date_start, payslip_run.date_end, states=["open", "close"]
        ).filtered(lambda c: c.active)
        contracts.generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env["hr.work.entry"].search([
            ("date_start", "<=", payslip_run.date_end + relativedelta(days=1)),
            ("date_stop", ">=", payslip_run.date_start + relativedelta(days=-1)),
            ("employee_id", "in", employees.ids),
        ])
        for slip in payslip_run.slip_ids:
            slip_tz = pytz.timezone(
                slip.contract_id.resource_calendar_id.tz
                or slip.employee_id.tz
                or slip.company_id.resource_calendar_id.tz
                or "UTC"
            )
            utc = pytz.timezone("UTC")
            date_from = slip_tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
            date_to = slip_tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
            payslip_work_entries = work_entries.filtered_domain([
                ("contract_id", "=", slip.contract_id.id),
                ("date_stop", "<=", date_to),
                ("date_start", ">=", date_from),
            ])
            payslip_work_entries._check_undefined_slots(slip.date_from, slip.date_to)

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in contracts:
            values = dict(default_values, **{
                "name": _("New Payslip"),
                "employee_id": contract.employee_id.id,
                "payslip_run_id": payslip_run.id,
                "date_from": payslip_run.date_start,
                "date_to": payslip_run.date_end,
                "contract_id": contract.id,
                "struct_id": self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)

        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()
        payslip_run.slip_ids.write({"state": "verify"})
        payslip_run.state = "verify"

        return success_result

    def _refresh_wizard(self):
        """Return action to reopen wizard without closing it."""
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",  # keep popup
            "context": self.env.context,  # keep current context
        }

    def action_select_all(self):
        """Mark all employees as removed (set is_remove=True)."""
        for wizard in self:
            wizard.line_ids.write({"is_remove": True})
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.employees",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",  # <- stay as wizard
        }

    def action_remove(self):
        """Delete employees where is_remove=True."""
        for wizard in self:
            to_remove = wizard.line_ids.filtered(lambda l: l.is_remove)
            to_remove.unlink()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.employees",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",  # <- stay as wizard
        }



class HrPayslipEmployeesLine(models.TransientModel):
    _name = "hr.payslip.employees.line"
    _description = "Payslip Employees Line"

    wizard_id = fields.Many2one("hr.payslip.employees", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", required=True)
    is_remove = fields.Boolean("Remove", default=False)

    # Related fields for display
    work_email = fields.Char(related="employee_id.work_email", readonly=True)
    department_id = fields.Many2one(related="employee_id.department_id", readonly=True)
    job_id = fields.Many2one(related="employee_id.job_id", readonly=True)
    structure_type_id = fields.Many2one(related="employee_id.structure_type_id", readonly=True)

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
            if contract.work_entry_source not in ['calendar','timesheet_hours']:
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
            payslip_run.state = 'verify'
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
    slip_id = fields.Many2one("hr.payslip", string="Slip_id",store=True)
    struct_id = fields.Many2one("hr.payroll.structure", string="Struct_id",store=True)

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


