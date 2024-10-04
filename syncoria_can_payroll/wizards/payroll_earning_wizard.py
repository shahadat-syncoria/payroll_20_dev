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

    pay_cycle = fields.Many2one("paycycle.config", string="Pay Cycle")
    date_from = fields.Date("From")
    date_to = fields.Date("From")

    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)

    @api.depends('pay_cycle')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle:
                rec.pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_ids.filtered(
                    lambda x: x.paycycle_config_id.id == rec.pay_cycle.id).ids

    def get_payslip_ids(self):
        payslip_ids = self.env['hr.payslip'].search([
            ('pay_cycle', '=', self.pay_cycle.id),
            ('state', 'in', ['paid']),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ],order= "date_from asc")

        payslip_data = []
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
            payslip_data.append({
                "pay_period": rec.pay_cycle_period.name.split(' Pay')[0],
                "employee_name": rec.employee_id.name,
                "total_gross": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "GROSS")]).amount,
                "total_insurable_earnings": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "I_Earning")]).amount,
                "net_pay": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "NET")]).amount,
                "fed_tax": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "FTAX")]).amount,
                "prov_tax": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "OTAX")]).amount,
                "cpp": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP")]).amount,
                "cpp2": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP2")]).amount,
                "ei": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI")]).amount,
                "employer_ei": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI_EMPLOYER")]).amount,

            })
            totals['total_gross'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "GROSS")]).amount
            totals['total_insurable_earnings'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "I_Earning")]).amount # Total Insurable Earnings
            totals['net_pay'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "NET")]).amount  # Net Pay
            totals['fed_tax'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "FTAX")]).amount  # Federal Tax Deduction
            totals['prov_tax'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "OTAX")]).amount  # Provincial Tax Deduction
            totals['cpp'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP")]).amount  # CPP Deduction
            totals['cpp2'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "CPP2")]).amount  # CPP2 Deduction
            totals['ei'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI")]).amount  # EI Deduction
            totals['employer_ei'] += rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "EI_EMPLOYER")]).amount # Employer EI Deduction
        datas = {
            'date_range': f"{self.date_from} to {self.date_to}",
            'payslips': payslip_data,
            'totals': totals,
        }
        return datas

    def print_report(self):
        datas = self.get_payslip_ids()
        return self.env.ref('syncoria_can_payroll.action_report_payroll_earning').report_action(self, data=datas)

    def get_xlsx_report(self):

        data = self.get_payslip_ids()
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
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format(
            {'font_size': '12px', 'align': 'center'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})
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

        sheet.write(row, col, 'Pay Period', bold)
        sheet.write(row, col + 1, 'Employee Name', bold)
        sheet.write(row, col + 2, 'Total Gross', bold)
        sheet.write(row, col + 3, 'Total Insurable Earnings', bold)
        sheet.write(row, col + 4, 'Net Pay', bold)
        sheet.write(row, col + 5, 'Federal Tax Deduction', bold)
        sheet.write(row, col + 6, 'Provincial Tax Deduction', bold)
        sheet.write(row, col + 7, 'CPP Deduction', bold)
        sheet.write(row, col + 8, 'CPP2 Deduction', bold)
        sheet.write(row, col + 9, 'EI Deduction', bold)
        sheet.write(row, col + 10, 'Employer EI Deduction', bold)

        for i, payslip in enumerate(data['payslips']):
            row += 1
            sheet.write(row, col, payslip['pay_period'])
            sheet.write(row, col + 1, payslip['employee_name'])
            sheet.write(row, col + 2, payslip['total_gross'])
            sheet.write(row, col + 3, payslip['total_insurable_earnings'])
            sheet.write(row, col + 4, payslip['net_pay'])
            sheet.write(row, col + 5, payslip['fed_tax'])
            sheet.write(row, col + 6, payslip['prov_tax'])
            sheet.write(row, col + 7, payslip['cpp'])
            sheet.write(row, col + 8, payslip['cpp2'])
            sheet.write(row, col + 9, payslip['ei'])
            sheet.write(row, col + 10, payslip['employer_ei'])
            # Adding totals
            totals['total_gross'] += payslip['total_gross']
            totals['total_insurable_earnings'] += payslip['total_insurable_earnings']
            totals['net_pay'] += payslip['net_pay']
            totals['fed_tax'] += payslip['fed_tax']
            totals['prov_tax'] += payslip['prov_tax']
            totals['cpp'] += payslip['cpp']
            totals['cpp2'] += payslip['cpp2']
            totals['ei'] += payslip['ei']
            totals['employer_ei'] += payslip['employer_ei']

        # Employer EI Deduction

        total_row = row + 2  # Row for totals
        sheet.write(total_row, col, 'Total', bold)  # Total label

        # Using Excel's SUM function to calculate totals
        sheet.write(total_row, col+2, totals['total_gross'])  # Total Gross
        sheet.write(total_row, col+3, totals['total_insurable_earnings'])  # Total Insurable Earnings
        sheet.write(total_row, col+4, totals['net_pay'])  # Net Pay
        sheet.write(total_row,col+5,  totals['fed_tax'])  # Federal Tax Deduction
        sheet.write(total_row, col+6, totals['prov_tax'])  # Provincial Tax Deduction
        sheet.write(total_row, col+7, totals['cpp'])  # CPP Deduction
        sheet.write(total_row, col+8, totals['cpp2'])  # CPP2 Deduction
        sheet.write(total_row, col+9, totals['ei'])  # EI Deduction
        sheet.write(total_row,  col+10,totals['employer_ei'])  # Employer EI Deduction

        workbook.close()
        output.seek(0)
        output.read()

        attachment_id = self.env['ir.attachment'].create({
            'name':  f"Payroll_Earning_Report_{self.date_from}_to_{self.date_to} - {_('XLSX report')}",
            'datas': base64.encodebytes(output.getvalue())
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }
