from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncoriaHrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    is_gross = fields.Boolean("Calculate as gross",default=False)
    deduct_from_gross = fields.Boolean("Deduct From Gross",default=False)
    is_insurable_hour = fields.Boolean("Calculate as Insurable Hour",default=False)
    is_negative_amount = fields.Boolean("Negative Amount",default=False)

    @api.constrains("is_gross","deduct_from_gross")
    def _constrain_is_gross_deduct_gross(self):
        for rec in self:
            if rec.is_gross and rec.deduct_from_gross:
                raise ValidationError(
                    "Both 'Calculate as gross' and 'Deduct From Gross' cannot be true at the same time.")




