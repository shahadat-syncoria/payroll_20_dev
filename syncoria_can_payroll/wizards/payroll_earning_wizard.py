import base64

from odoo import fields, models, _, api
import io
import json
import xlsxwriter
from odoo import models
from odoo.tools import date_utils
from datetime import datetime, date
import calendar

class EmployeeNetPay(models.TransientModel):
    _name = "payroll.earning.wizard"
    _description = "Payroll Earning Report"


    date_from = fields.Date("Date From",default=lambda self: date(date.today().year, 1, 1))
    date_to = fields.Date("Date To",default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        ))

    payslip_state = fields.Selection([("paid","Paid"),("done","Done"),("validated","Waiting"),("all","All")],
                                     string="Payslip State", default="paid")

    def get_payslip_ids(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ]
        if self.payslip_state and self.payslip_state != 'all':
            domain += [('state', '=', self.payslip_state)]
        else:
            domain += [('state', 'not in', ['cancel', 'draft'])]

        payslip_ids = self.env['hr.payslip'].search(domain, order="date_from asc")

        currency = self.env.company.currency_id
        grouped_payslip_data = {}
        totals = {
            'cpp': 0.0,
            'cpp2': 0.0,
            'ei': 0.0,
            'employer_ei': 0.0,
            'fed_tax': 0.0,
            'net_pay': 0.0,
            'prov_tax': 0.0,
            'total_gross': 0.0,
            'total_insurable_earnings': 0.0,
            'employer_contribution': 0.0,
            'wsib': 0.0
        }

        for rec in payslip_ids:
            wsib_rate = rec.company_id.wsib
            employee = rec.employee_id
            line_ids = rec.line_ids

            def get_amount(code):
                return line_ids.filtered(lambda l: l.code == code).amount or 0.0

            insurable_earnings = get_amount("I_Earning")
            wsib_amount = (insurable_earnings * wsib_rate) / 100

            pay_cycle = rec.pay_cycle.paystub_group_name
            if pay_cycle not in grouped_payslip_data:
                grouped_payslip_data[pay_cycle] = {
                    "pay_period": rec.pay_cycle_period.name if rec.pay_cycle_period else '',
                    "payslips": []
                }

            payslip_data = {
                "pay_period": rec.pay_cycle_period.name if rec.pay_cycle_period else '',
                "employee_name": employee.name,
                "employee_code": '',
                "total_gross": get_amount("GROSS"),
                "total_insurable_earnings": insurable_earnings,
                "net_pay": get_amount("NET"),
                "fed_tax": get_amount("FTAX"),
                "prov_tax": get_amount("OTAX"),
                "cpp": get_amount("CPP"),
                "cpp2": get_amount("CPP2"),
                "ei": get_amount("EI"),
                "employer_ei": get_amount("EI_EMPLOYER"),
                "employer_contribution": get_amount("EMP_CON"),
                "wsib": wsib_amount
            }

            # Add to totals
            totals['total_gross'] += payslip_data['total_gross']
            totals['total_insurable_earnings'] += payslip_data['total_insurable_earnings']
            totals['net_pay'] += payslip_data['net_pay']
            totals['fed_tax'] += payslip_data['fed_tax']
            totals['prov_tax'] += payslip_data['prov_tax']
            totals['cpp'] += payslip_data['cpp']
            totals['cpp2'] += payslip_data['cpp2']
            totals['ei'] += payslip_data['ei']
            totals['employer_ei'] += payslip_data['employer_ei']
            totals['employer_contribution'] += payslip_data['employer_contribution']
            totals['wsib'] += wsib_amount

            grouped_payslip_data[pay_cycle]['payslips'].append(payslip_data)

        datas = {
            'date_range': f"{self.date_from} to {self.date_to}",
            'grouped_payslips': grouped_payslip_data,
            'totals': totals,
            'currency': currency.symbol
        }

        return datas


    def print_report(self):
        datas = self.get_payslip_ids()
        return self.env.ref('syncoria_can_payroll.action_report_payroll_earning').with_context(landscape=True).report_action(self, data=datas)

    def get_xlsx_report(self):
        data = self.get_payslip_ids()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format({'font_size': '12px', 'align': 'center'})
        head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': '20px'})
        txt = workbook.add_format({'font_size': '10px', 'align': 'center'})
        bold = workbook.add_format({'bold': True})
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:L', 20)

        sheet.merge_range('B2:L3', 'Payroll Earning Report', head)
        sheet.merge_range('D4:E4', 'Date Range:', cell_format)
        sheet.merge_range('F4:G4', data['date_range'], txt)

        row = 6
        col = 1

        # Header
        sheet.write(row, col, 'Pay Cycle', bold)
        sheet.write(row, col + 1, 'Pay Period', bold)
        sheet.write(row, col + 2, 'Employee Name', bold)
        sheet.write(row, col + 3, 'Total Gross', bold)
        sheet.write(row, col + 4, 'Total Insurable Earnings', bold)
        sheet.write(row, col + 5, 'Net Pay', bold)
        sheet.write(row, col + 6, 'Federal Tax Deduction', bold)
        sheet.write(row, col + 7, 'Provincial Tax Deduction', bold)
        sheet.write(row, col + 8, 'CPP Deduction', bold)
        sheet.write(row, col + 9, 'CPP2 Deduction', bold)
        sheet.write(row, col + 10, 'EI Deduction', bold)
        sheet.write(row, col + 11, 'Employer EI Deduction', bold)
        sheet.write(row, col + 12, 'WSIB Premium', bold)

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

        for pay_cycle, cycle_data in data['grouped_payslips'].items():
            # Write pay cycle and pay period header
            sheet.write(row + 1, col, pay_cycle)


            for payslip in cycle_data['payslips']:
                row += 1
                sheet.write(row , col + 1, payslip['pay_period'])
                sheet.write(row, col + 2, payslip['employee_name'])
                sheet.write(row, col + 3, payslip['total_gross'])
                sheet.write(row, col + 4, payslip['total_insurable_earnings'])
                sheet.write(row, col + 5, payslip['net_pay'])
                sheet.write(row, col + 6, payslip['fed_tax'])
                sheet.write(row, col + 7, payslip['prov_tax'])
                sheet.write(row, col + 8, payslip['cpp'])
                sheet.write(row, col + 9, payslip['cpp2'])
                sheet.write(row, col + 10, payslip['ei'])
                sheet.write(row, col + 11, payslip['employer_ei'])
                sheet.write(row, col + 12, payslip['wsib'])

                # Update totals
                totals['total_gross'] += payslip['total_gross']
                totals['total_insurable_earnings'] += payslip['total_insurable_earnings']
                totals['net_pay'] += payslip['net_pay']
                totals['fed_tax'] += payslip['fed_tax']
                totals['prov_tax'] += payslip['prov_tax']
                totals['cpp'] += payslip['cpp']
                totals['cpp2'] += payslip['cpp2']
                totals['ei'] += payslip['ei']
                totals['employer_ei'] += payslip['employer_ei']
                totals['wsib'] += payslip['wsib']

        row += 1  # Leave a blank row between different pay cycles
        sheet.write(row, col, 'Total', bold)  # Total label

            # Write totals for the current pay cycle
        sheet.write(row, col + 3, totals['total_gross'])
        sheet.write(row, col + 4, totals['total_insurable_earnings'])
        sheet.write(row, col + 5, totals['net_pay'])
        sheet.write(row, col + 6, totals['fed_tax'])
        sheet.write(row, col + 7, totals['prov_tax'])
        sheet.write(row, col + 8, totals['cpp'])
        sheet.write(row, col + 9, totals['cpp2'])
        sheet.write(row, col + 10, totals['ei'])
        sheet.write(row, col + 11, totals['employer_ei'])
        sheet.write(row, col + 12, totals['wsib'])



        row += 1  # Move to the next row for the next pay cycle

        workbook.close()
        output.seek(0)


        attachment_id = self.env['ir.attachment'].create({
            'name':  f"Payroll_Earning_Report_{self.date_from}_to_{self.date_to} - {_('XLSX report')}",
            'datas': base64.encodebytes(output.getvalue())
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }
