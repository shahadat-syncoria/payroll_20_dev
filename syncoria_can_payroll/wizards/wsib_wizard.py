from datetime import date
import calendar

from odoo import fields, models


class EmployeeWSIBReport(models.TransientModel):
    _name = "wsib.wizard"
    _description = "WSIB Report"

    date_from = fields.Date(
        "Date From",
        default=lambda self: date(date.today().year, 1, 1),
    )
    date_to = fields.Date(
        "Date To",
        default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        ),
    )
    payslip_state = fields.Selection(
        [("paid", "Paid"), ("validated", "Waiting"), ("all", "All")],
        string="Payslip State",
        default="paid",
    )

    def _get_payslip_domain(self):
        self.ensure_one()

        domain = [
            ("pay_date", ">=", self.date_from),
            ("pay_date", "<=", self.date_to),
        ]

        if self.payslip_state and self.payslip_state != "all":
            domain.append(("state", "=", self.payslip_state))
        else:
            domain.append(("state", "not in", ["cancel", "draft"]))

        return domain

    def _get_line_amount(self, line_ids, code):
        line = line_ids.filtered(lambda l: l.code == code)[:1]
        return line.amount if line else 0.0

    def _get_wsib_base(self, line_ids):
        insurable_earning = self._get_line_amount(line_ids, "I_Earning")
        if insurable_earning:
            return insurable_earning

        return sum(line.amount for line in line_ids if line.salary_rule_id.is_wsib)

    def get_payslip_ids(self):
        payslip_ids = self.env["hr.payslip"].search(self._get_payslip_domain(), order="date_from asc")
        payslip_list = []
        currency = self.env.company.currency_id
        totals = {
            "total_wsib_base": 0.0,
            "total_wsib_amount_assessed": 0.0,
        }

        for payslip in payslip_ids:
            employee = payslip.employee_id
            line_ids = payslip.line_ids
            total_wsib_base = self._get_wsib_base(line_ids)
            wsib_amount = self._get_line_amount(line_ids, "WSIB")

            if not wsib_amount:
                wsib_rate = payslip.company_id.wsib or 0.0
                wsib_amount = (total_wsib_base * wsib_rate) / 100

            name_parts = (employee.name or "").split()
            payslip_data = {
                "pay_period": payslip.pay_cycle_period.name if payslip.pay_cycle_period else "",
                "employee_last_name": name_parts[-1] if name_parts else "",
                "employee_first_name": name_parts[0] if name_parts else "",
                "employee_code": employee.employee_code if "employee_code" in employee._fields else "",
                "wsib_base": total_wsib_base,
                "wsib_amount_assessed": wsib_amount,
            }
            payslip_list.append(payslip_data)
            totals["total_wsib_base"] += payslip_data["wsib_base"]
            totals["total_wsib_amount_assessed"] += payslip_data["wsib_amount_assessed"]

        payslip_list = sorted(payslip_list, key=lambda x: (x["employee_code"] or "").lower())

        return {
            "date_range": f"{self.date_from} to {self.date_to}",
            "totals": totals,
            "payslips": payslip_list,
            "currency": currency.symbol,
        }

    def print_report(self):
        datas = self.get_payslip_ids()
        return self.env.ref("syncoria_can_payroll.action_report_wsib").report_action(self, data=datas)
