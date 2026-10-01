from odoo import api, fields, models



class InheritedContract(models.Model):
    _inherit = "hr.version"


    is_timesheet_based = fields.Boolean(
        string="Timesheet Based", groups="hr.group_hr_user",
        help="When enabled, payslip hours are computed from the employee's timesheets.")
    work_entry_source = fields.Selection(selection_add=[('timesheet_hours', 'Timesheet Hours')])

    @api.depends('is_timesheet_based')
    def _compute_work_entry_source(self):
        super()._compute_work_entry_source()
        for version in self.filtered('is_timesheet_based'):
            version.work_entry_source = 'timesheet_hours'

    # def generate_work_entries(self, date_start, date_stop, force=False):
    #     # for contract in self:
    #     #     if contract.work_entry_source == 'timesheet_hours':
    #     #         continue
    #     # self = self.filtered(lambda w: w.work_entry_source != 'timesheet_hours')
    #
    #     return super().generate_work_entries(date_start, date_stop, force)

    # v20: the former `_get_attendance_intervals` override (which forced 'calendar' and 'timesheet_hours'
    # versions to use the calendar attendance intervals) is no longer needed: hr.version now decides through
    # `has_static_work_entries()` (= not attendance_based) and its signature
    # `calendar._attendance_intervals_batch(start_dt, end_dt, resources_per_tz=None, domain=None)` changed.

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
