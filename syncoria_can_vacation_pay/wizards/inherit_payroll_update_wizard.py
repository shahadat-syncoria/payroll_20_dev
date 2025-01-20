from odoo import models, fields, api

class InheritPayrollUpdateWizard(models.TransientModel):
    _inherit = 'payroll.update.wizard'

    def update_payroll_info(self):
        res = super(InheritPayrollUpdateWizard, self).update_payroll_info()
        for x in self.employee_ids:
            line_obj = x.payroll_line_ids.filtered(lambda x: x.year == str(2024))

            line_obj.ytd_vac_pay_amount = x.ytd_vac_pay_amount
            line_obj.ytd_vac_pay_amount_erp = x.ytd_vac_pay_amount_erp
            line_obj.previous_vac_pay_amount = x.previous_vac_pay_amount
            line_obj.vac_pay_amount_taken = x.vac_pay_amount_taken

        return res

    def update_remaining_vacation_info(self):
        for x in self.employee_ids:
            line_obj = x.payroll_line_ids.filtered(lambda x: x.year == str(2025))
            if line_obj:
                x.ytd_vac_pay_amount = line_obj.ytd_vac_pay_amount
