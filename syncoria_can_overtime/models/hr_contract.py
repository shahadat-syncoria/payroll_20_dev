from odoo import api,fields,models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    overtime_threshold = fields.Float(string='Overtime Threshold')