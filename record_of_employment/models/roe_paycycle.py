from odoo import fields, models, api, _


class RoePaycycle(models.Model):
    _name = "roe.paycycle"
    _description = "Record of employment paycycle"

    pay_period_date = fields.Date("Pay Period Ending Date")
    insurable_earning = fields.Float("Insurable Earning")
    insurable_hour = fields.Float("Insurable Hour")
    employee_id = fields.Many2one("hr.employee")

    _unique_pay_period_employee = models.Constraint(
        "UNIQUE(pay_period_date, employee_id)",
        "The pay period date must be unique for each employee!"
    )
