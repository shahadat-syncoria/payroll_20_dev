import base64

from odoo import fields, models, _, api
import io
import json
import xlsxwriter
from odoo import models
from odoo.tools import date_utils
from ..helper.helper_functions import year_selection


class EmployeeNetPay(models.TransientModel):
    _name = "employee.net.pay.wizard"
    _description = "Employee Net Pay Report"

    pay_cycle = fields.Many2one("paycycle.config", string="Pay Cycle")
    payperiod = fields.Many2one("paycycle.period", string="Pay Period")
    department_id = fields.Many2one("hr.department", string="Department")

    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)

    year = fields.Selection(
        year_selection,
        default=lambda self: str(fields.Date.today().year),
        string="Year"
    )

    @api.depends('pay_cycle','year')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle and rec.year:
                rec.pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_year_slab_ids.paycycle_period_ids.filtered(
                    lambda x: x.year == rec.year).ids

    def get_payslip_ids(self):
        payslip_ids = self.env['hr.payslip'].search(
            [('pay_cycle_period', '=', self.payperiod.id), ("state", "in", ['paid', 'done'])])
        payslip_data = []
        for rec in payslip_ids:
            payslip_data.append({
                "reference": rec.number,
                "payslip_name": rec.name,
                "employee_name": rec.employee_id.name,
                "job_position": rec.employee_id.job_id.name or " ",
                "bank_account": rec.employee_id.bank_account_id.acc_number or " ",
                "amount": rec.line_ids.search([("slip_id", "=", rec.id), ("code", "=", "NET")]).amount

            })
        datas = {
            'pay_cycle': self.pay_cycle.paystub_group_name,
            'pay_period': self.payperiod.name,
            'payslips': payslip_data
        }
        return datas

    def print_report(self):
        datas = self.get_payslip_ids()
        return self.env.ref('syncoria_can_payroll.action_report_employee_net_pay').report_action(self, data=datas)

    def get_xlsx_report(self):

        data = self.get_payslip_ids()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format(
            {'font_size': '12px', 'align': 'center'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})
        txt = workbook.add_format({'font_size': '10px', 'align': 'center'})
        bold = workbook.add_format({'bold': True})
        sheet.set_column('E:E', 45)
        sheet.set_column('F:I', 15)

        sheet.merge_range('B2:I3', 'Employee Net Pay', head)

        sheet.merge_range('D4:E4', 'Pay Cycle:', cell_format)
        sheet.merge_range('F4:G4', data['pay_cycle'], txt)
        sheet.merge_range('D5:E5', 'Pay Period:', cell_format)
        sheet.merge_range('F5:G5', data['pay_period'], txt)

        row = 6
        col = 3

        sheet.write(row, col, 'Payslip Reference', bold)
        sheet.write(row, col + 1, 'Payslip Name', bold)
        sheet.write(row, col + 2, 'Employee Name', bold)
        sheet.write(row, col + 3, 'Job Position', bold)
        sheet.write(row, col + 4, 'Bank Account', bold)
        sheet.write(row, col + 5, 'Net Salary', bold)

        for i, payslip in enumerate(data['payslips']):
            row += 1

            sheet.write(row, col, payslip['reference'])
            sheet.write(row, col + 1, payslip['payslip_name'])
            sheet.write(row, col + 2, payslip['employee_name'])
            sheet.write(row, col + 3, payslip['job_position'])
            sheet.write(row, col + 4, payslip['bank_account'])
            sheet.write(row, col + 5, payslip['amount'])

        workbook.close()
        output.seek(0)
        output.read()

        attachment_id = self.env['ir.attachment'].create({
            'name': f"{self.display_name} - {_('XLSX report')}",
            'datas': base64.encodebytes(output.getvalue())
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }
