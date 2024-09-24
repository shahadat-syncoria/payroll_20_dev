from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncoriaHrWorkEntryTypeVacation(models.Model):
    _inherit = "hr.work.entry.type"

    is_adjusted_with_vacation_pay = fields.Boolean("Is adjusted with vacation pay?",default=False)