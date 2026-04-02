from odoo import fields, models, api, _



class StatutoryHoliday(models.Model):
    _name = "statutory.holiday"
    _description = "Statutory Holiday Amount"

    roe_id = fields.Many2one("record.of.employee")
    statutory_date = fields.Date("Date")
    statutory_amount = fields.Float(string="Amount")


class StatutoryHoliday(models.Model):
    _name = "other.monies"
    _description = "Other Monies Amount"

    roe_id = fields.Many2one("record.of.employee")
    name = fields.Char("Name")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    amount = fields.Float(string="Amount")




