from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class SyncoriaHrWorkEntryTypeVacation(models.Model):
    _inherit = "hr.work.entry.type"

    is_adjusted_with_vacation_pay = fields.Boolean("Is adjusted with vacation pay?",default=False)


class SyncoriaHrVacation(models.Model):
    _inherit = "hr.payslip.input"

    @api.constrains("amount")
    def vacation_pay_amount(self):
        vacation_input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id
        for rec in self:
            if rec.input_type_id.id == vacation_input_type and rec.amount > rec.payslip_id.ytd_vac_pay_amount and not rec.payslip_id.employee_id.is_vacation_pay_adjust_negative:
                raise UserError("Vacation pay amount cannot be greater then Remaining Vacation Pay.")

