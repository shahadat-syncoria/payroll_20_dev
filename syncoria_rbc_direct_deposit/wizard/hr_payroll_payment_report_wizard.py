import base64
import csv
from datetime import datetime

from io import StringIO

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_list
from odoo.tools.misc import format_date


class HrPayrollPaymentReportWizardInherit(models.TransientModel):

    _inherit = 'hr.payroll.payment.report.wizard'
    _description = 'HR Payroll Payment Report Wizard'

    export_format = fields.Selection(
        selection_add=[('txt', 'TXT')],
        ondelete={
            'txt': 'cascade',
        }
    )

    def _create_txt_binary(self):


        # Fetch required fields for the header
        client_number = self.env.company.partner_id.rbc_client_number.zfill(10)  # Ensure it's 10 digits
        client_name = self.env.company.partner_id.name.ljust(30)[:30]  # Left-justify and truncate to 30 characters
        today = datetime.today()
        julian_date = f"{today.year}{today.timetuple().tm_yday:03d}"

        currency = self.env.company.partner_id.currency_id.name  # CAD or USD
        file_creation_number = "TEST"
        language_code= "E"
        country= "CAN"
        # Example employee data
        employees = [
            {
                "customer_number": employee.employee_id.barcode or "DEFAULT",  # Replace with actual employee VAT or another unique identifier
                "payment_number": i + 1,
                "institution_number": employee.employee_id.bank_account_id.bank_id.bic,  # Your logic here
                "branch_number": employee.employee_id.bank_account_id.rbc_bank_transit_no,  # Your logic here
                "account_number": employee.employee_id.bank_account_id.acc_number or "DEFAULT_ACCOUNT",  # Replace with employee's actual account
                "payment_amount": employee.net_wage or 0.0,  # Assuming you have total amount on the payslip
                "payment_date": f"{employee.paid_date.year}{employee.paid_date.timetuple().tm_yday:03d}",
                "customer_name": employee.employee_id.name.ljust(30)[:30],
                 # Replace with actual data
            }
            for i, employee in enumerate(self.payslip_ids)
        ]
        total_payment_amount = sum(employee["payment_amount"] for employee in employees)
        # Use "TEST" for testing, otherwise use a unique number
        output = StringIO()
        # Add the header line based on the RBC Header Record specification
        output.write(
            f"$$AA01STD0152[TEST[NL$$\n"
            f"000001AHDR{client_number}{client_name}{file_creation_number}{julian_date}{currency}1".ljust(152)
        )
        output.write("\n")



        # Generate Basic Payment Records for all employees
        record_count = 2
        for employee in employees:

            customer_number = employee['customer_number'].ljust(19)[:19]  # Ensure 19 characters
            payment_number = f"{employee['payment_number']}"
            institution_number = f"{employee['institution_number']}"
            branch_number = f"{employee['branch_number']}"
            account_number = employee['account_number'].ljust(18)[:18]  # 18-character account number
            payment_amount = f"{int(employee['payment_amount'] * 100):010d}"  # Amount in cents
            payment_date = employee['payment_date']  # Julian date (YYYYDDD)
            customer_name = employee['customer_name'].ljust(30)[:30]  # 30-character customer name
            # language_code = employee['language_code'][:1]  # Language code (E or F)
            # destination_currency = employee['destination_currency'].ljust(3)[:3]  # CAD or USD
            # destination_country = employee['destination_country'].ljust(3)[:3]  # CAN or USA

            # Create Basic Payment Record
            record = (
                f"{record_count:06d}C"  # Record count (6 digits)
                f"200"  # Transaction code (default blank for now)
                f"{client_number}"
                f" "  # Filler
                f"{customer_number}"
                f"{payment_number}"
                f"{institution_number}{branch_number}"
                f"{account_number}"
                f" "  # Filler
                f"{payment_amount}"
                f"      "  # Reserved (6 blanks)
                f"{payment_date}"
                f"{customer_name}"
                f"{language_code}"
                f" " 
                f"{client_name}"
                  
                f"{currency}"
                f" "  # Reserved
                f"{country}"
                f"    "  # Filler (2 blanks)
                 # Reserved (2 blanks)
                f"N"  # Optional record indicator
            ).ljust(152)  # Pad to 152 characters
            output.write(record + "\n")  # Add newline after each record
            record_count += 1
        output.write(
            f"{record_count:06d}ZTRL{client_number}{len(employees):06d}{int(total_payment_amount * 100):014d}{len(employees):06d}".ljust(152)

        )
        # Encode the content to Base64
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

