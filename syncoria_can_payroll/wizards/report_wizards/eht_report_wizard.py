from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
from ...helper.helper_functions import year_selection,month_selection
import calendar
import requests
from urllib.parse import urlsplit, urlunsplit

class EHTReportWizard(models.TransientModel):
    _name = "eht.report.wizard"
    _description = "EHT Report Wizard"

    file_data = fields.Binary('Report')
    year = fields.Selection(
        year_selection,
        string="Year",
        default=lambda self: str(datetime.now().year - 1) if datetime.now().month == 1 else str(datetime.now().year)
    )
    month = fields.Selection(
        month_selection,
        string="Month",
        default=lambda self: str((datetime.now().month - 1) or 12)  # Handles January case
    )

    def eht_report_pdf(self):
        data = self.eht_report_orm()

        return self.env.ref(
            'syncoria_can_payroll.eht_report_tmpl_id').with_context(landscape=True).report_action(self, data=data)


    def eht_report_orm(self):
        selected_year = int(self.year)
        selected_month = int(self.month)
        month_name = calendar.month_name[selected_month]
        # Calculate the start and end date range for filtering
        date_start = datetime(selected_year, 1, 1).strftime('%Y-%m-%d')  # January 1st
        # Get last day of the selected month
        last_day = calendar.monthrange(selected_year, selected_month)[1]  # Returns (weekday, last_day)
        date_end = datetime(selected_year, selected_month, last_day).strftime('%Y-%m-%d')  # Last day of selected month

        # Fetch payslips from January to the selected month
        payslip_ids = self.env['hr.payslip'].search([
            ('state', '=', 'paid'),
            ('date_from', '>=', date_start),
            ('date_to', '<=', date_end)
        ])

        total_tax = 0
        total_payroll = sum(payslip.net_wage for payslip in payslip_ids)
        exemption_amount = self.env.company.exemption_amount
        taxable_amount = 0
        rate = 0
        if total_payroll > exemption_amount:
            taxable_amount = total_payroll - exemption_amount
            total_tax,rate = self._calculate_tax(taxable_amount)

        data = {
            'model': 'eht.report.wizard',
            'form': self.read()[0],
            'total_tax': round(total_tax,2),
            'year': str(self.year),
            'total_payroll': round(total_payroll, 2),
            'exemption_amount': round(exemption_amount, 2),
            'taxable_amount': round(taxable_amount, 2),
            'rate': rate,
            'month_name': month_name,
        }
        return data


    def _calculate_tax(self, taxable_amount):
        payload = {
            "taxable_amount": taxable_amount,
        }
        total_tax, rate = 0, 0
        # Make the API call ******************************************************************
        try:
            with_user = self.env['ir.config_parameter'].sudo()
            base_url = with_user.get_param('syncoria_can_payroll.base_url')
            if not base_url:
                raise ValidationError(f"Failed to call the API, Need to configure a base url from the settings.")

            # Process the base URL to remove extra / if present.
            final_url = self._process_base_url(base_url)

            token = with_user.get_param('syncoria_can_payroll.token')
            # Define the API endpoint and headers
            endpoint = '/api/v1/payroll_info/calculate_eht/'
            headers = {
                'Authorization': f'Token {token}'
            }

            # Make the API request
            response = requests.get(final_url + endpoint, json=payload, headers=headers)
            response_data = response.json()

            if response_data:
                total_tax = response_data.get('tax', 0)
                rate = response_data.get('rate', 0)
            else:
                raise ValidationError("Invalid response from the API. Could not calculate the tax.")

        except Exception as e:
            raise ValidationError(f"Error during API call: {str(e)}")

        return round(total_tax, 2), rate

    def _process_base_url(self, base_url):
        """
        Process the base URL to remove extra / if present.
        """
        split_url = urlsplit(base_url)
        if split_url.port == 8000:
            new_netloc = split_url.hostname + (f":{split_url.port}" if split_url.port else "")
        else:
            new_netloc = split_url.netloc
        return urlunsplit((split_url.scheme, new_netloc, '', '', ''))
