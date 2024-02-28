from odoo import fields, models


class PayrollResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vac_pay_type = fields.Selection([
        ('time_wise', 'Store Time'),
        ('cash_wise', 'Store Amount'),
    ], default='time_wise', required=True, string='Vacation Pay Type', config_parameter='syncoria_can_vacation_pay.vac_pay_type')

    vacation_report = fields.Selection([('days','Days'),('hours','Hours'),('both','Both')], default="days", string="Vacation Report" ,
                                       config_parameter='syncoria_can_vacation_pay.vac_report')
