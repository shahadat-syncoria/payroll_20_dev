from collections import defaultdict
import pytz

from pytz import timezone

from odoo import fields, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class InheritedContract(models.Model):
    _inherit = "hr.contract"


    work_entry_source = fields.Selection(selection_add=[('timesheet_hours', 'Timesheet Hours')],
                                         ondelete={'timesheet_hours': 'set default'})

    # def _recompute_work_entries(self, date_from, date_to):
    #     self.ensure_one()
    #     if self.work_entry_source == 'timesheet_hours':
    #         pass
    #     else:
    #         super(InheritedContract,self)._recompute_work_entries(date_from, date_to)

    def generate_work_entries(self, date_start, date_stop, force=False):
        # for contract in self:
        #     if contract.work_entry_source == 'timesheet_hours':
        #         continue
        self = self.filtered(lambda w: w.work_entry_source != 'timesheet_hours')

        return super().generate_work_entries(date_start, date_stop, force)

