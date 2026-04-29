from collections import defaultdict

from odoo import api, models, _

class InheritedHrPayslipYTD(models.Model):
    _inherit = 'hr.payslip'


    def _get_last_ytd_payslips(self):
        if not self:
            return self

        earliest_date_to = min(self.mapped('date_to'))
        earliest_ytd_date_to = min(
            company.get_last_ytd_reset_date(earliest_date_to) for company in self.company_id
        )
        ytd_payslips_grouped = self.env['hr.payslip']._read_group(
            domain=[
                ('employee_id', 'in', self.employee_id.ids),
                ('struct_id', 'in', self.struct_id.ids),
                # ('ytd_computation', '=', True),
                ('date_to', '>=', earliest_ytd_date_to),
                ('date_to', '<=', max(self.mapped('date_to'))),
                ('state', 'in', ['paid']),
            ],
            groupby=['employee_id', 'struct_id'],
            aggregates=['id:recordset']
        )

        ytd_payslips_sorted = defaultdict(lambda: self.env['hr.payslip'])
        for employee_id, struct_id, payslips in ytd_payslips_grouped:
            ytd_payslips_sorted[(employee_id, struct_id)] = payslips.sorted(
                key=lambda p: p.date_to, reverse=True
            )

        last_ytd_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            last_payslips = ytd_payslips_sorted[(payslip.employee_id, payslip.struct_id)].filtered(
                lambda p: p.date_to <= payslip.date_to
            )
            if last_payslips and last_payslips[0].date_to >=\
                    payslip.company_id.get_last_ytd_reset_date(payslip.date_to):
                last_ytd_payslips[payslip] = last_payslips[0]

        return last_ytd_payslips

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