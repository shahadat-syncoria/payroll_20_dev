from odoo import api, fields, models,_
from odoo.tools import float_round


class HrEmployeeOvertime(models.Model):
    _inherit = "hr.employee"


    overtime_method = fields.Selection([('no_overtime', 'No Overtime'),
                                        ('banked_overtime', 'Banked Overtime'),
                                        ('paycycle_out', 'Payout by Paycycle')],default='no_overtime', string='Overtime Method')
    total_stored_overtime=fields.Float("Stored Overtime Hours", compute='_compute_total_store_overtime')
    total_stored_overtime_amount=fields.Float("Stored Overtime Amount", compute='_compute_total_store_overtime')

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
            "views": [[False, "tree"]],
            "context": {
                "create": 0
            },
            "domain": [('employee_id', '=', self.id)]
        }
