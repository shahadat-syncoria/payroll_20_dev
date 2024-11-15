from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncoriaHrWorkEntryType(models.Model):
    _inherit = "hr.salary.rule"

    is_insurable_earning = fields.Boolean("Calculate as Insurable Earning",default=False,
                                          help="This rule in payslip will be calculated as Insurable Earning, if this field is true. ")
    is_pensionable = fields.Boolean("Calculate as Pensionable",default=False,
                                    help="This rule in payslip will be calculated in CPP and CPP2, if this field is true. ")
    is_vacation_pay = fields.Boolean("Accrued Vacation Pay",default=False,
                                     help="This rule in payslip will be calculated for storing the vacation pay, if this field is true. ")
    is_irregular_payment = fields.Boolean("Calculate as Irregular Payment",default=False)
    cat_code = fields.Char(related="category_id.code", string="Category Code")





