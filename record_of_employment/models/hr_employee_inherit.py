from odoo import api, fields, models



class HrEmployeeInherit(models.Model):
    _inherit = "hr.employee"

    roe_paycycle_ids = fields.One2many("roe.paycycle","employee_id")

    def action_roe_paycyle_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'ROE Previous paycycle',
            'res_model': 'roe.paycycle.excel.wizard',
            'view_mode': 'form',
            'target': 'new',
        }


