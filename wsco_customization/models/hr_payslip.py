from odoo import fields, models, _, api


class InheritedHrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _payslip_line_ytd_total(self):
        for rec in self:
            # Get the YTD payslip lines for the employee and year
            line_ids = rec.employee_id._get_ytd_payslip_line_ids(rec.year)

            # Get the salary rules associated with the employee's contract structure
            rules = rec.employee_id.contract_id.structure_type_id.default_struct_id.rule_ids

            # Create a dictionary to store YTD totals for each rule
            ytd_totals = {}

            for rule in rules:
                # Filter the lines for the current rule and sum their total amounts
                rule_lines = line_ids.filtered(lambda line: line.salary_rule_id == rule)
                ytd_totals[rule.code] = round(sum(rule_lines.mapped('total')),2)

            # Save the dictionary to an attribute (optional, or use as needed)
            return ytd_totals

