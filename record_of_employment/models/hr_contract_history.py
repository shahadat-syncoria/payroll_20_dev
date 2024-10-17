from odoo import fields, models, api, _


class InheritedHrContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    is_vacation_pay_paid = fields.Boolean(default=False, compute="compute_is_vacation_pay_paid")

    def compute_is_vacation_pay_paid(self):
        """
        Working but need to change the process. because everytime the function called.
        """
        if self.employee_id.ytd_vac_pay_amount == 0.0:
            self.is_vacation_pay_paid = True
        else:
            self.is_vacation_pay_paid = False

    def vacation_pay(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "hr.vacation.pay",
            "context": {"default_employee_id": self.id,
                        "default_duration": round(self.employee_id.allocated_vacation_leave,2),
                        "default_vacation_remain":  round(self.employee_id.allocated_vacation_leave,2),
                        "default_is_last_pay": True},
            "name": _("Vacation Pay Request"),
            "target": "new",
            'view_mode': 'form',
        }
        return result

    def roe_generation(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "record.of.employee",
            "context": {"default_employee_id": self.id},
            "name": _("ROE"),
            "target": "new",
            'view_mode': 'form',
        }
        return result
