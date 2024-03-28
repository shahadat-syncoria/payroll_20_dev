from odoo import api, fields, models


class SyncoriaHrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    is_gross = fields.Boolean("Calculate as gross",default=False)



