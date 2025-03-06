from odoo import fields, models, api, _


class RoePaycycle(models.Model):
    _name = "roe.paycycle"
    _description = "Record of employment paycycle"

    _sql_constraints = [
        ('unique_pay_period_employee', 'UNIQUE(pay_period_date, employee_id)',
         'The pay period date must be unique for each employee!')
    ]

    pay_period_date = fields.Date("Pay Period Ending Date")
    insurable_earning = fields.Float("Insurable Earning")
    insurable_hour = fields.Float("Insurable Hour")
    employee_id = fields.Many2one("hr.employee")