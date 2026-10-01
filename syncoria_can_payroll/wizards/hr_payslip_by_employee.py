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

        # Odoo 20: hr.work.entry records no longer exist, work entries are generated on the fly
        # by hr.version.generate_work_entries() as a list of vals dicts.
        WorkEntryType = self.env['hr.work.entry.type']

        # Try to detect "attendance" types robustly across versions:
        attendance_types = WorkEntryType.search([
            ('code', 'in', ['002.00','TIMESHEET_WORK100'])
        ])

        versions = self.env['hr.version']
        for version_set in employee._get_contracts(date_start, date_end).values():
            versions |= version_set
        if not versions:
            return 0.0

        total_hours = 0.0
        for vals in versions.generate_work_entries(date_start, date_end):
            if vals['employee_id'] != employee:
                continue
            if attendance_types and vals['work_entry_type_id'] not in attendance_types:
                continue
            if not date_start <= vals['date'] <= date_end:
                continue
            total_hours += vals['duration']

        return total_hours

    @api.model
    def _get_default_attendance_hours(self, hr_payslip_run, employee):

        if not employee.version_id.is_hourly:
            return self._get_attendance_hours(employee, hr_payslip_run.date_start, hr_payslip_run.date_end)
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

    def _filter_contracts(self, contracts):
        # Could be overriden to avoid having 2 'end of the year bonus' payslips, etc.
        return contracts

    def compute_sheet(self):
        self.ensure_one()
        ctx = self.env.context
        pay_cycle_period = ctx.get("pay_cycle_period")
        # pay_cycle = ctx.get("pay_cycle")
        pay_cycle = self.env['paycycle.config'].browse(
            self.env.context.get('pay_cycle', {}).get('id')
        )
        year =  self.env['paycycle.period'].browse(
            self.env.context.get('pay_cycle_period', {}).get('id')
        ).year

        # --------------------------------------------------
        # 1️⃣ Resolve or create payslip run
        # --------------------------------------------------
        run_created = False
        if ctx.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(ctx['active_id'])
        else:
            run_created = True
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

            # Odoo 20: structure_id is required on the pay run
            structure = (ctx.get('raw_record') or {}).get('structure_id') or {}
            structure_id = structure.get('id') if isinstance(structure, dict) else structure
            payslip_run = self.env['hr.payslip.run'].create({
                'name': f"{pay_cycle_period['display_name'] } - {year}" ,
                'structure_id': structure_id or False,
                'pay_cycle': pay_cycle.id,
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
        # 4️⃣ Work entries
        # --------------------------------------------------
        # Odoo 20: work entries are no longer persisted (hr.work.entry is gone), they are generated
        # when the payslip worked days lines are computed, so there is nothing to generate/validate here.
        if run_created:
            payslip_run.version_ids = versions
        else:
            payslip_run.version_ids |= versions

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
                'struct_id': payslip_run.structure_id.id or version.structure_type_id.default_struct_id.id,
                'pay_cycle_period':pay_cycle_period.get('id'),
                "payout_vacation_pay_paycycle": version.employee_id.payout_vacation_pay_paycycle,

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

        return  payslip_run.action_open_payslips()


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
            if rec.ytd_vac_pay_amount < rec.vac_pay and not rec.employee_id.is_vacation_pay_adjust_negative:
                raise UserError("Vacation pay amount cannot be greater then Remaining Vacation Pay.")


