from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncoriaHrWorkEntryType(models.Model):
    _inherit = "hr.salary.rule"

    is_insurable_earning = fields.Boolean("Calculate as Insurable Earning",default=False)
    is_pensionable = fields.Boolean("Calculate as Pensionable",default=False)
    is_vacation_pay = fields.Boolean("Calculate as Vacation Pay",default=False)
    cat_code = fields.Char(related="category_id.code", string="Category Code")



