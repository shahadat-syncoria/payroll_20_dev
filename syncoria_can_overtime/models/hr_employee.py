from odoo import api, fields, models,_
from odoo.tools import float_round


class HrEmployeeOvertime(models.Model):
    _inherit = "hr.employee"


    overtime_method = fields.Selection([('no_overtime', 'No Overtime'),
                                        ('banked_overtime', 'Banked Overtime'),
                                        ('paycycle_out', 'Payout by Paycycle')],default='no_overtime', string='Overtime Method',groups="hr.group_hr_user")
    total_stored_overtime=fields.Float("Stored Overtime Hours", compute='_compute_total_store_overtime', digits=(16, 2))
    total_stored_overtime_amount=fields.Float("Stored Overtime Amount", compute='_compute_total_store_overtime')
    overtime_threshold = fields.Float(readonly=False, related="version_id.overtime_threshold", inherited=True, groups="hr.group_hr_manager")
    overtime_threshold_selection = fields.Selection(readonly=False, related="version_id.overtime_threshold_selection", inherited=True, groups="hr.group_hr_manager")

    overtime_threshold_id = fields.Many2one(readonly=False, related="version_id.overtime_threshold_id", inherited=True, groups="hr.group_hr_manager")

    def _compute_total_store_overtime(self):
        for rec in self:
            overtime_records = self.env["hr.attendance.overtime.store"].search([("employee_id", "=", rec.id)])
            rec.total_stored_overtime = sum(overtime_records.mapped("duration_remaining"))
            rec.total_stored_overtime_amount = sum(overtime_records.mapped("remaining_amount"))


    def action_open_overtime_store(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Stored Overtime"),
            "res_model": "hr.attendance.overtime.store",
            "views": [[False, "list"]],
            "context": {
                "create": 0
            },
            "domain": [('employee_id', '=', self.id)]
        }
