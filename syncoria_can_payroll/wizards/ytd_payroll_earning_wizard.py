import base64
from datetime import datetime, date
import calendar

from odoo import fields, models, _, api
import io
import json
import xlsxwriter
from odoo import models
from odoo.tools import date_utils
from ..helper.helper_functions import year_selection


class YTDPayrollEarning(models.TransientModel):
    _name = "ytd.payroll.earning.wizard"
    _description = "YTD Payroll Earning Report"

    period_type = fields.Selection(
        selection=[
            ('year', 'Year'),
            ('date_range', 'Date Range'),
        ],
        string="Period Type",
        required=True,
        default='year',
    )

    year = fields.Selection(
        year_selection,
        string="Year",
        default=lambda self: str(fields.Date.today().year),
        required=True
    )

    date_from = fields.Date(
        string="Date From",
        default=lambda self: date(date.today().year, 1, 1)
    )

    date_to = fields.Date(
        string="Date To",
        default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        )
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees",
        compute="_compute_employee_ids",
        store=True,
    )
    payslip_state = fields.Selection([("paid", "Paid"),
                                      ("done", "Done"),
                                      ("validated", "Waiting"),
                                      ("all", "All")],
                                     string="Payslip State", default="paid")

    @api.depends('date_from','date_to')
    def _compute_employee_ids(self):
        for wizard in self:
            wizard.employee_ids = [(5, 0, 0)]  # Clear first


            if wizard.period_type == "year":
                year_int = int(wizard.year)
                start_of_year = date(year_int, 1, 1)
                end_of_year = date(year_int, 12, 31)
            else:
                start_of_year = self.date_from
                end_of_year = self.date_to

            contracts = self.env['hr.version'].search([
                ('active', '!=', False),
                '|', ('date_end', '>=', start_of_year), ('date_end', '=', False),
                ('date_start', '<=', end_of_year),
            ])
            employee_ids = contracts.mapped('employee_id').ids
            wizard.employee_ids = [(6, 0, employee_ids)]


    def get_payslip_totals(self):
        if self.period_type == "year":
            year_int = int(self.year)
            date_from = date(year_int, 1, 1)
            date_to = date(year_int, 12, 31)
        else:
            date_from = self.date_from
            date_to = self.date_to
        currency = self.env.company.currency_id.symbol

        all_employee_totals = []
        domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to)
        ]
        if self.payslip_state and self.payslip_state != 'all':
            domain += [('state', '=', self.payslip_state)]
        else:
            domain += [('state', 'not in', ['cancel', 'draft'])]


        for employee in self.employee_ids:

            payslips = self.env['hr.payslip'].search(domain+[('employee_id', '=', employee.id)])

            totals = {
                'total_gross': 0.0,
                'total_insurable_earnings': 0.0,
                'net_pay': 0.0,
                'fed_tax': 0.0,
                'prov_tax': 0.0,
                'cpp': 0.0,
                'cpp2': 0.0,
                'ei': 0.0,
                'employer_ei': 0.0,
                'wsib': 0.0,
            }

            for slip in payslips:
                wsib_rate = slip.company_id.wsib or 0.0

                def get(code):
                    line = slip.line_ids.filtered(lambda l: l.code == code)
                    return line.amount if line else 0.0

                gross = get("GROSS")
                insurable = get("I_Earning")
                net = get("NET")
                ftax = get("FTAX")
                otax = get("OTAX")
                cpp = get("CPP")
                cpp2 = get("CPP2")
                ei = get("EI")
                ei_employer = get("EI_EMPLOYER")
                wsib = (insurable * wsib_rate) / 100.0

                totals['total_gross'] += gross
                totals['total_insurable_earnings'] += insurable
                totals['net_pay'] += net
                totals['fed_tax'] += ftax
                totals['prov_tax'] += otax
                totals['cpp'] += cpp
                totals['cpp2'] += cpp2
                totals['ei'] += ei
                totals['employer_ei'] += ei_employer
                totals['wsib'] += wsib

            all_employee_totals.append({
                'employee_name': employee.name,
                'totals': totals,

            })
        datas={
            "year": self.year,
            "date_from" : date_from,
            "date_to" : date_to,
            "employee_totals":all_employee_totals,
            'currency': currency
        }
        return datas

    def print_report(self):
        datas = self.get_payslip_totals()
        return self.env.ref('syncoria_can_payroll.action_report_ytd_payroll_earning').with_context(landscape=True).report_action(self, data=datas)

    def get_xlsx_report(self):
        data = self.get_payslip_totals()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format({'font_size': 12, 'align': 'center'})
        head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 20})
        txt = workbook.add_format({'font_size': 10, 'align': 'center'})
        bold = workbook.add_format({'bold': True, 'align': 'center'})

        # Set column widths
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:N', 20)

        # Header
        sheet.merge_range('B2:N3', ' Year To Date Payroll Earning Report', head)
        sheet.merge_range('F4:G4', 'Date Range:', bold)
        sheet.merge_range('H4:I4', f"{data['date_from']} - {data['date_to']}", bold)

        row = 6
        col = 1

        # Column titles
        headers = [
            'Employee Name', 'Total Gross', 'Total Insurable Earnings', 'Net Pay',
            'Federal Tax Deduction', 'Provincial Tax Deduction', 'CPP Deduction',
            'CPP2 Deduction', 'EI Deduction', 'Employer EI Deduction', 'WSIB Premium'
        ]
        for i, header in enumerate(headers):
            sheet.write(row, col + i, header, bold)

        # Initialize totals
        totals = {
            'total_gross': 0.0,
            'total_insurable_earnings': 0.0,
            'net_pay': 0.0,
            'fed_tax': 0.0,
            'prov_tax': 0.0,
            'cpp': 0.0,
            'cpp2': 0.0,
            'ei': 0.0,
            'employer_ei': 0.0,
            'wsib': 0.0
        }

        currency = data.get('currency', '')

        # Loop through employees
        for emp in data['employee_totals']:
            row += 1
            emp_name = emp['employee_name']
            emp_totals = emp['totals']

            sheet.write(row, col + 0, emp_name)
            sheet.write(row, col + 1, emp_totals['total_gross'])
            sheet.write(row, col + 2, emp_totals['total_insurable_earnings'])
            sheet.write(row, col + 3, emp_totals['net_pay'])
            sheet.write(row, col + 4, emp_totals['fed_tax'])
            sheet.write(row, col + 5, emp_totals['prov_tax'])
            sheet.write(row, col + 6, emp_totals['cpp'])
            sheet.write(row, col + 7, emp_totals['cpp2'])
            sheet.write(row, col + 8, emp_totals['ei'])
            sheet.write(row, col + 9, emp_totals['employer_ei'])
            sheet.write(row, col + 10, emp_totals['wsib'])

            # Accumulate totals
            for key in totals:
                totals[key] += emp_totals.get(key, 0.0)

        # Final total row
        row += 2
        sheet.write(row, col, 'TOTAL', bold)
        sheet.write(row, col + 1, totals['total_gross'], bold)
        sheet.write(row, col + 2, totals['total_insurable_earnings'], bold)
        sheet.write(row, col + 3, totals['net_pay'], bold)
        sheet.write(row, col + 4, totals['fed_tax'], bold)
        sheet.write(row, col + 5, totals['prov_tax'], bold)
        sheet.write(row, col + 6, totals['cpp'], bold)
        sheet.write(row, col + 7, totals['cpp2'], bold)
        sheet.write(row, col + 8, totals['ei'], bold)
        sheet.write(row, col + 9, totals['employer_ei'], bold)
        sheet.write(row, col + 10, totals['wsib'], bold)

        # Save and return file
        workbook.close()
        output.seek(0)

        attachment_id = self.env['ir.attachment'].create({
            'name': f"Payroll_Earning_Report_{data['date_from']} - {data['date_to']}.xlsx",
            'datas': base64.encodebytes(output.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}?download=true",
            "target": "self",
        }


