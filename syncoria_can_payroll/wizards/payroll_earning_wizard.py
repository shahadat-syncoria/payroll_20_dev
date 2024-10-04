import base64

from odoo import fields, models, _, api
import io
import json
import xlsxwriter
from odoo import models
from odoo.tools import date_utils


class EmployeeNetPay(models.TransientModel):
    _name = "payroll.earning.wizard"
    _description = "Payroll Earning Report"


    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")

    def get_payslip_ids(self):
        payslip_ids = self.env['hr.payslip'].search([
            ('state', 'in', ['paid']),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ], order="date_from asc")

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
            'total_insurable_earnings': 0.0
        }

        for rec in payslip_ids:
            pay_cycle = rec.pay_cycle.paystub_group_name
            if pay_cycle not in grouped_payslip_data:
                grouped_payslip_data[pay_cycle] = {
                    "pay_period": rec.pay_cycle_period.name.split(' Pay')[0],
                    "payslips": []
                }

            payslip_data = {
                "pay_period": rec.pay_cycle_period.name.split(' Pay')[0],
                "employee_name": rec.employee_id.name,
                "total_gross": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "GROSS")]).amount,
                "total_insurable_earnings": rec.line_ids.search(
                    [("slip_id", "=", rec.id), ("code", "=", "I_Earning")]).amount,
                "net_pay": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "NET")]).amount,
                "fed_tax": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "FTAX")]).amount,
                "prov_tax": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "OTAX")]).amount,
                "cpp": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP")]).amount,
                "cpp2": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP2")]).amount,
                "ei": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI")]).amount,
                "employer_ei": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI_EMPLOYER")]).amount,
            }
            totals['total_gross'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "GROSS")]).amount
            totals['total_insurable_earnings'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "I_Earning")]).amount  # Total Insurable Earnings
            totals['net_pay'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "NET")]).amount  # Net Pay
            totals['fed_tax'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "FTAX")]).amount  # Federal Tax Deduction
            totals['prov_tax'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "OTAX")]).amount  # Provincial Tax Deduction
            totals['cpp'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "CPP")]).amount  # CPP Deduction
            totals['cpp2'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "CPP2")]).amount  # CPP2 Deduction
            totals['ei'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI")]).amount  # EI Deduction
            totals['employer_ei'] += rec.line_ids.search(
                [("slip_id", "=", rec.id), ("code", "=", "EI_EMPLOYER")]).amount  # Employer EI Deduction

            # Append the payslip data to the appropriate pay_cycle group
            grouped_payslip_data[pay_cycle]['payslips'].append(payslip_data)



        datas = {
            'date_range': f"{self.date_from} to {self.date_to}",
            'grouped_payslips': grouped_payslip_data,
            'totals': totals,
        }
        return datas



    def print_report(self):
        datas = self.get_payslip_ids()
        return self.env.ref('syncoria_can_payroll.action_report_payroll_earning').report_action(self, data=datas)

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
        sheet.set_column('C:C', 20)
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

        totals = {
            'total_gross': 0.0,
            'total_insurable_earnings': 0.0,
            'net_pay': 0.0,
            'fed_tax': 0.0,
            'prov_tax': 0.0,
            'cpp': 0.0,
            'cpp2': 0.0,
            'ei': 0.0,
            'employer_ei': 0.0
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
