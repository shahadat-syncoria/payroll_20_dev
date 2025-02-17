import base64
import csv
from datetime import datetime

from io import StringIO

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.tools.misc import format_date


class HrPayrollPaymentReportWizard(models.TransientModel):

    _name = 'hr.payroll.deposit.report.wizard'
    _description = 'HR Payroll deposit Report Wizard'

    payslip_run_id = fields.Many2one('hr.payslip.run')
    payslip_ids = fields.Many2many('hr.payslip', required=True)
    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('txt', 'TXT'),
    ], string='Export Format', required=True, default='csv')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _create_txt_binary(self):

        client_number = self.env.company.partner_id.rbc_client_number.zfill(10)
        client_name = self.env.company.partner_id.name
        today = datetime.today()
        julian_date = f"{today.year}{today.timetuple().tm_yday:03d}"
        currency = self.env.company.partner_id.currency_id.name
        file_creation_number = "TEST"  # for production we need to remove test with meaningful number
        language_code = "E"
        country = "CAN"
        record_count = 1

        valid_employees = []
        errors = []

        if not client_number:
            errors.append(f"Missing RBC assigned client number for the company")

        output = StringIO()
        output.write(
            f"$$AA01STD0152[TEST[NL$$"
        )
        output.write("\r\n")
        output.write(
            f"{record_count:06d}AHDR{client_number}{client_name.ljust(30)[:30]}{file_creation_number}{julian_date}{currency}1".ljust(
                152) + "\r\n"
        )
        # output.write("\n")

        for i, employee in enumerate(self.payslip_ids):
            try:
                # Validate Required Fields
                customer_number = employee.employee_id.barcode
                institution_number = getattr(employee.employee_id.bank_account_id.bank_id, 'bic', '')
                branch_number = getattr(employee.employee_id.bank_account_id, 'rbc_bank_transit_no', '')
                account_number = getattr(employee.employee_id.bank_account_id, 'acc_number', '')
                employee_currency_name = getattr(employee.employee_id.bank_account_id.currency_id, 'display_name', '')
                payment_amount = employee.net_wage or 0.0
                payment_date = f"{employee.paid_date.year}{employee.paid_date.timetuple().tm_yday:03d}"
                customer_name = employee.employee_id.name

                # Check for missing or invalid values
                if not customer_number:
                    errors.append(f"Missing Customer Number for {employee.employee_id.name}")
                if not len(customer_number) <= 19:
                    errors.append(f"Employee Batch ID Can't exceed 19 Digits/Character for {employee.employee_id.name}")
                if not institution_number:
                    errors.append(f"Missing Institution Number for {employee.employee_id.name}")
                if len(institution_number) != 4:
                    errors.append(f"Institution Number Must Be 4 Digits for {employee.employee_id.name}")
                if not branch_number:
                    errors.append(f"Missing Branch Number for {employee.employee_id.name}")
                if not account_number:
                    errors.append(f"Missing Account Number for {employee.employee_id.name}")
                if not payment_amount:
                    errors.append(f"Missing Payment Amount for {employee.employee_id.name}")

                if not errors:  # Only add employee if no errors
                    valid_employees.append({
                        "customer_number": customer_number.ljust(4),
                        "payment_number": i + 1,
                        "institution_number": institution_number,
                        "branch_number": branch_number.ljust(5)[:5],
                        "account_number": account_number,
                        "employee_currency_name": employee_currency_name,
                        "payment_amount": payment_amount,
                        "payment_date": payment_date,
                        "customer_name": customer_name.ljust(30)[:30],
                    })

            except Exception as e:
                errors.append(str(e))

        # Log errors if any
        if errors:
            self.payslip_run_id.message_post(body="<br/>".join(errors))
            self.payslip_run_id.direct_deposit_txt = None
            self.env.cr.commit()
            raise ValidationError(
                _("There are some missing information. Please refresh the browser and check the log for more details."))

        else:
            total_payment_amount = sum(emp["payment_amount"] for emp in valid_employees)
            record_count += 1

            for employee in valid_employees:
                record = (
                             f"{record_count:06d}C"
                             f"200"  # may need to replace with meaningful number
                             f"{client_number}"
                             f" "
                             f"{employee['customer_number'].ljust(19)[:19]}"
                             f"{employee['payment_number']:02d}"
                             f"{employee['institution_number']}{employee['branch_number']}"
                             f"{employee['account_number'].ljust(18)[:18]}"
                             f" "
                             f"{int(employee['payment_amount'] * 100):010d}"
                             f"      "
                             f"{employee['payment_date']}"
                             f"{employee['customer_name']}"
                             f"{language_code}"
                             f" "
                             f"{client_name.ljust(15)[:15]}"
                             f"{employee['employee_currency_name']}"
                             f" "
                             f"{country}"
                             f"    "
                             f"N"
                         ).ljust(152) + "\r\n"
                output.write(record)
                record_count += 1

            output.write(
                f"{record_count:06d}ZTRL{client_number}{len(valid_employees):06d}{int(total_payment_amount * 100):014d}{'0' * 28}".ljust(
                    152) + "\r\n"
            )

            content = output.getvalue()
            return base64.encodebytes(content.encode())

    def _write_file_txt(self, payment_report, extension, filename=''):

        filename = filename or self.payslip_run_id.name or self.payslip_ids[:1].name

        if self.payslip_run_id and extension == '.txt':
            self.payslip_run_id.write({
                'direct_deposit_txt': payment_report,
                'direct_deposit_txt_filename': filename + extension,
                'direct_deposit_txt_date': fields.Date.today()})

        # self.payslip_ids.write({
        #     'direct_deposit_txt': payment_report,
        #     'direct_deposit_txt_filename': filename + extension,
        #     'direct_deposit_txt_date': fields.Date.today()})

    def generate_txt_payment_report(self):
        self.ensure_one()
        if self.export_format == 'txt':
            payment_report = self._create_txt_binary()
            self._write_file_txt(payment_report, '.txt')
