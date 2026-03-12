# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, date, time, timedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date
from dateutil.relativedelta import relativedelta




class HrPayslipEmployeesLine(models.TransientModel):
    _name = "hr.payslip.employees.line"
    _description = "Payslip Employees Line"

    # wizard_id = fields.Many2one("hr.payslip.employees", required=True, ondelete="cascade")
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


    def _get_attendance_hours(self, employee, date_start,date_end):
        # Build an inclusive datetime window for the payslip run
        if isinstance(date_start, str):
            date_start = fields.Date.from_string(date_start)
        if isinstance(date_end, str):
            date_end = fields.Date.from_string(date_end)

        start_dt = datetime.combine(date_start, time.min)
        end_dt = datetime.combine(date_end, time.min)

        WorkEntry = self.env['hr.work.entry']
        WorkEntryType = self.env['hr.work.entry.type']

        # Try to detect "attendance" types robustly across versions:
        attendance_types = WorkEntryType.search([
            ('code', 'in', ['WORK100','TIMESHEET_WORK100'])
        ])

        domain = [
            ('employee_id', '=', employee.id),
            # overlap with [start_dt, end_dt)
            ('date', '<=', end_dt),
            ('date', '>=', start_dt),
        ]
        if attendance_types:
            domain.append(('work_entry_type_id', 'in', attendance_types.ids))

        entries = WorkEntry.search(domain)

        total_hours = 0.0
        for we in entries:

            total_hours += we.duration

        return total_hours

    @api.model
    def _get_default_attendance_hours(self, hr_payslip_run, employee):

        if not employee.version_id.is_hourly:
            return self._get_attendance_hours(hr_payslip_run, employee)
        else:
            return 0.0

    def _default_manual_input_ids(self):

        ctx = self.env.context

        date_start = ctx.get("date_start")
        date_end = ctx.get("date_end")



        if ctx.get("selected_employee_ids"):
            employees = self.env['hr.employee'].browse(ctx["selected_employee_ids"])

            return [
                (0, 0, {
                    "employee_id": emp.id,
                    "attendance_hours": self._get_attendance_hours(
                        emp, date_start, date_end
                    ),
                    "ytd_vac_pay_amount": emp.ytd_vac_pay_amount,
                })
                for emp in employees
            ]





    manual_input_ids = fields.One2many("hr.employee.manual.input.line", 'manual_input_wizard_id', default=lambda self: self._default_manual_input_ids())

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.version_id] |= work_entry

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
        ctx = self.env.context
        pay_cycle_period = ctx.get("pay_cycle_period")

        # --------------------------------------------------
        # 1️⃣ Resolve or create payslip run
        # --------------------------------------------------
        if ctx.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(ctx['active_id'])
        else:
            date_start = fields.Date.to_date(ctx.get('date_start'))
            date_end = fields.Date.to_date(ctx.get('date_end'))

            if not date_start or not date_end:
                raise UserError(_("Start date and End date are required."))

            today = fields.Date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)

            if date_start == first_day and date_end == last_day:
                name = date_start.strftime('%B %Y')
            else:
                name = _('From %s to %s') % (
                    fields.Date.to_string(date_start),
                    fields.Date.to_string(date_end),
                )

            payslip_run = self.env['hr.payslip.run'].create({
                'name': name,
                'date_start': date_start,
                'date_end': date_end,
                'company_id': self.env.company.id,
            })

        # --------------------------------------------------
        # 2️⃣ Employees from wizard
        # --------------------------------------------------
        employees = self.manual_input_ids.with_context(active_test=False).employee_id
        if not employees:
            raise UserError(_("You must select employee(s)."))

        # Prevent duplicate slips
        employees -= payslip_run.slip_ids.employee_id
        if not employees:
            payslip_run.state = '01_ready'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.run',
                'views': [[False, 'form']],
                'res_id': payslip_run.id,
            }

        # --------------------------------------------------
        # 3️⃣ Get VALID versions (same as generate_payslips)
        # --------------------------------------------------
        contracts_map = employees._get_contracts(
            payslip_run.date_start,
            payslip_run.date_end
        )

        versions = self.env['hr.version']
        for version_set in contracts_map.values():
            versions |= version_set

        if not versions:
            raise UserError(_("No valid payroll versions found."))

        # --------------------------------------------------
        # 4️⃣ Generate work entries (CORE PAYROLL LOGIC)
        # --------------------------------------------------
        versions.generate_work_entries(
            payslip_run.date_start,
            payslip_run.date_end
        )

        all_work_entries = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('employee_id', 'in', versions.employee_id.ids),
                ('date', '<=', payslip_run.date_end),
                ('date', '>=', payslip_run.date_start),
            ],
            groupby=['version_id'],
            aggregates=['id:recordset'],
        ))

        # --------------------------------------------------
        # 5️⃣ Undefined slot checks (timezone-safe)
        # --------------------------------------------------
        utc = pytz.utc
        for tz, slips_per_tz in payslip_run.slip_ids.grouped(lambda s: s.version_id.tz).items():
            slip_tz = pytz.timezone(tz or utc)
            for slip in slips_per_tz:
                date_from = slip_tz.localize(
                    datetime.combine(slip.date_from, time.min)
                ).astimezone(utc).replace(tzinfo=None)

                date_to = slip_tz.localize(
                    datetime.combine(slip.date_to, time.max)
                ).astimezone(utc).replace(tzinfo=None)

                if version_work_entries := all_work_entries.get(slip.version_id):
                    version_work_entries.filtered_domain([
                        ('date', '<=', date_to),
                        ('date', '>=', date_from),
                    ])
                    version_work_entries._check_undefined_slots(slip.date_from, slip.date_to)

        for work_entries in all_work_entries.values():
            work_entries = work_entries.filtered(lambda we: we.state != 'validated')
            if work_entries._check_if_error():
                conflicts = work_entries.filtered(lambda we: we.state == 'conflict')._to_intervals()
                time_intervals_str = "".join(
                    f"\n - {s} → {e} ({we.employee_id.name})"
                    for s, e, we in conflicts._items
                )
                raise UserError(
                    _("Some work entries could not be validated. Time intervals to look for:%s", time_intervals_str)
                )

        # --------------------------------------------------
        # 6️⃣ Create payslips (same structure as run)
        # --------------------------------------------------
        Payslip = self.env['hr.payslip']
        default_vals = Payslip.default_get(Payslip.fields_get())
        payslip_vals = []

        for version in versions[::-1]:
            payslip_vals.append(default_vals | {
                'name': _('New Payslip'),
                'employee_id': version.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'version_id': version.id,
                'company_id': payslip_run.company_id.id,
                'pay_cycle_period':pay_cycle_period.get('id')
            })

        payslip_run.slip_ids |= Payslip.with_context(tracking_disable=True).create(payslip_vals)

        # --------------------------------------------------
        # 7️⃣ Compute payslips with manual inputs
        # --------------------------------------------------
        payslip_run.slip_ids._compute_name()
        for slip in payslip_run.slip_ids:
            slip.compute_workdays_manual_input(self.manual_input_ids)
            slip.compute_sheet()

        payslip_run.state = '01_ready'

        return 1

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


