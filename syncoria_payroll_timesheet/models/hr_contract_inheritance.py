from odoo import api, fields, models
from odoo.exceptions import UserError


class InheritedContract(models.Model):
    _inherit = "hr.contract"


    work_entry_source = fields.Selection(selection_add=[('timesheet_hours', 'Timesheet Hours')],
                                         ondelete={'timesheet_hours': 'set default'})
