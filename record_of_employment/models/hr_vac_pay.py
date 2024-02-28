from odoo import fields, models, api, _


class RoeVacationPay(models.Model):
    _inherit = 'hr.vacation.pay'

    roe_id = fields.Many2one("record.of.employee", string="Roe")
