from odoo import models, fields, api
from odoo.exceptions import ValidationError

class OvertimePolicy(models.Model):
    _name = 'overtime.thresholds'
    _description = 'Overtime Threshold'

    name = fields.Char(string='Name', required=True)
    line_ids = fields.One2many('overtime.thresholds.line', 'overtime_threshold_id', string='Overtime Rules')


class OvertimePolicyRule(models.Model):
    _name = 'overtime.thresholds.line'
    _description = 'Overtime Threshold Line'

    overtime_threshold_id = fields.Many2one('overtime.thresholds', string='Overtime Threshold', ondelete='cascade', required=True)
    work_entry_id = fields.Many2one("hr.work.entry.type", string ="Work Entry Type",required=True)
    start_threshold = fields.Float(string='Start Threshold (hours)', required=True)
    end_threshold = fields.Float(string='End Threshold (hours)', required=True)
    overtime_rate = fields.Integer(string='Overtime Parameter value', required=True)

    @api.constrains('start_threshold', 'end_threshold')
    def _check_thresholds(self):
        for rec in self:
            if rec.end_threshold <= rec.start_threshold:
                raise ValidationError(
                    "End Threshold must be greater than Start Threshold."
                )
