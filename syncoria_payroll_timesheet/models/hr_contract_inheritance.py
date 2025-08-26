from collections import defaultdict
import pytz

from pytz import timezone

from odoo import fields, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class InheritedContract(models.Model):
    _inherit = "hr.contract"


    work_entry_source = fields.Selection(selection_add=[('timesheet_hours', 'Timesheet Hours')],
                                         ondelete={'timesheet_hours': 'set default'})



    def generate_work_entries(self, date_start, date_stop, force=False):
        # for contract in self:
        #     if contract.work_entry_source == 'timesheet_hours':
        #         continue
        # self = self.filtered(lambda w: w.work_entry_source != 'timesheet_hours')

        return super().generate_work_entries(date_start, date_stop, force)

    def _get_attendance_intervals(self, start_dt, end_dt):
        mapped_intervals = super()._get_attendance_intervals(start_dt, end_dt)
        # {resource: intervals}
        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        for contract in self:
            if contract.work_entry_source not in ['calendar','timesheet_hours']:
                continue
            employees_by_calendar[contract.resource_calendar_id] |= contract.employee_id
        result = dict()
        for calendar, employees in employees_by_calendar.items():
            mapped_intervals.update(calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources=employees.resource_id,
                tz=pytz.timezone(calendar.tz)
            ))
        return mapped_intervals


    # def _get_work_entries_values(self, date_start, date_stop):
    #     """
    #     Make 'timesheet_hours' behave like 'working_schedule' for monthly contracts,
    #     without breaking Odoo's bulk attendance fetching.
    #     """
    #     # Change the work_entry_source in context for the batch of matching contracts
    #     monthly_timesheet_contracts = self.filtered(
    #         lambda c: c.work_entry_source == 'timesheet_hours' and c.wage_type == "monthly"
    #     )
    #
    #     other_contracts = self - monthly_timesheet_contracts
    #
    #     # Apply fake source in context for the monthly_timesheet_contracts
    #     monthly_timesheet_contracts = monthly_timesheet_contracts.with_context(
    #         force_work_entry_source='calendar'
    #     )
    #
    #     # Combine both sets back into a single recordset
    #     combined_contracts = monthly_timesheet_contracts | other_contracts
    #
    #     # Now call super() ONCE for the whole set
    #     return super(InheritedContract, combined_contracts)._get_work_entries_values(date_start, date_stop)
    #
    # def generate_work_entries(self, date_start, date_stop, force=False):
    #     # Skip hourly + timesheet_hours contracts
    #     contracts = self.filtered(lambda w: not (w.work_entry_source == 'timesheet_hours' and w.wage_type == "hourly"))
    #     return super(InheritedContract, contracts).generate_work_entries(date_start, date_stop, force)
