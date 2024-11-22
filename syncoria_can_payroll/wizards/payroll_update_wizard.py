from odoo import models, fields, api

class PayrollUpdateWizard(models.TransientModel):
    _name = 'payroll.update.wizard'
    _description = "Batch Update Payroll Info"

    employee_ids = fields.Many2many('hr.employee',string="Employee")

    def default_get(self, fields):
        defaults = super(PayrollUpdateWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            employee = self.env["hr.employee"].search([("id", "in", active_ids)])
            defaults['employee_ids'] = [(6, 0,employee.ids)]

        return defaults


    def update_payroll_info(self):
        for x in self.employee_ids:
            line_obj = x.payroll_line_ids.filtered(lambda x: x.year == str(2024))
            if line_obj:
                continue
            if not line_obj:
                line_obj = self.env["hr.employee.ytd.payroll.information"].create(
                    {
                        "head_id": x.id,
                        "year": str(2024),
                    }
                )

            line_obj.ytd_cpp_erp = x.ytd_cpp_erp
            line_obj.ytd_previous_cpp = x.ytd_previous_cpp
            line_obj.ytd_cpp = x.ytd_cpp

            line_obj.ytd_cpp2_erp = x.ytd_cpp2_erp
            line_obj.ytd_previous_cpp2 = x.ytd_previous_cpp2
            line_obj.ytd_cpp2 = x.ytd_cpp2

            line_obj.ytd_ei_erp = x.ytd_ei_erp
            line_obj.ytd_previous_ei = x.ytd_previous_ei
            line_obj.ytd_ei = x.ytd_ei

            line_obj.ytd_ei_employer_erp = x.ytd_ei_employer_erp
            line_obj.ytd_previous_ei_employer = x.ytd_previous_ei_employer
            line_obj.ytd_ei_employer = x.ytd_ei_employer

            line_obj.ytd_pi_erp = x.ytd_pi_erp
            line_obj.ytd_pi = x.ytd_pi
            line_obj.ytd_previous_pi = x.ytd_previous_pi

            line_obj.year_to_date_irregular_payment = x.year_to_date_irregular_payment
            line_obj.ytd_previous_irre_payment = x.ytd_previous_irre_payment
            line_obj.ytd_previous_irre_payment_erp = x.ytd_previous_irre_payment_erp




