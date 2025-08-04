from odoo.exceptions import UserError
from odoo import models, api, fields, _

class HrPayslipDalton(models.Model):
    _inherit = 'paycycle.period'


    overtime_start_date = fields.Date("Overtime Start Period")
    overtime_end_date = fields.Date("Overtime End Period")