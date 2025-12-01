from odoo import api,fields,models

class HrContract(models.Model):
    _inherit = 'hr.version'

    overtime_threshold = fields.Float(string='Overtime Threshold')

    overtime_threshold_selection = fields.Selection([("fixed","Fixed"),("range","Range")],string='Overtime Threshold Selection',default="fixed")

    overtime_threshold_id = fields.Many2one("overtime.thresholds")