from odoo import fields, models, api, _
from odoo.exceptions import UserError

class InheritedContractVac(models.Model):
    _inherit = 'hr.contract'

    def create(self, vals):
        res = super(InheritedContractVac, self).create(vals)

        # Ensure `structure_type_id` is provided in `vals`
        if "structure_type_id" in vals:
            # Get the structure type and its default structure
            structure_type = self.env["hr.payroll.structure.type"].browse(vals["structure_type_id"])
            struct_id = structure_type.default_struct_id

            # Search for the ACCRUED_VP salary rule
            accrued_vp_accounting = self.env["hr.salary.rule"].search([
                ("struct_id", "=", struct_id.id),
                ("code", "=", "ACCRUED_VP")
            ], limit=1)

            if accrued_vp_accounting:
                # Write the accounts to the related employee
                res.employee_id.write({
                    "account_debit": accrued_vp_accounting.account_debit.id,
                    "account_credit": accrued_vp_accounting.account_credit.id
                })

        return res

    def write(self, vals):
        res = super(InheritedContractVac, self).write(vals)
        if "structure_type_id" in vals:
            employee =self.employee_id
            struct_id= self.structure_type_id.default_struct_id
            accrued_vp_accounting = self.env["hr.salary.rule"].search(
                [("struct_id", "=", struct_id.id), ("code", "=", "ACCRUED_VP")])
            if employee.account_debit and employee.account_credit:
                employee.write({
                    "account_debit" : accrued_vp_accounting.account_debit,
                    "account_credit" :accrued_vp_accounting.account_credit
                })
        return res


