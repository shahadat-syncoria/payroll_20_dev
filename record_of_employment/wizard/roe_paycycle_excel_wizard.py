from odoo import models, fields, api, _
import base64
import pandas as pd
from io import BytesIO
from odoo import models
import io
import base64
import xlsxwriter
from datetime import datetime


from odoo.exceptions import UserError,ValidationError

class ProductProcessingExcelWizard(models.TransientModel):
    _name = "roe.paycycle.excel.wizard"
    _description = "ROE Paycycle Excel Wizard"

    excel_file = fields.Binary(string="File", help="Date format should be DD/MM/YY")

    def button_process(self):
        if not self.excel_file:
            raise ValidationError(_("Please select an Excel File"))
        try:
            # Odoo 20: Binary fields hold a BinaryValue (raw bytes), not base64
            data = self.excel_file.content
            excel_data = pd.read_excel(BytesIO(data))
        except Exception as e:
            raise ValidationError(_("Error reading the Excel file: %s" % str(e)))

        lines = []
        for index, row in excel_data.iterrows():

            raw_date = row.get('Pay Period Ending Date')

            # ✅ Handle different formats safely
            if pd.notna(raw_date):
                if isinstance(raw_date, pd.Timestamp):
                    pay_date = raw_date.date()
                else:
                    # assuming format DD/MM/YY
                    pay_date = datetime.strptime(str(raw_date), "%d/%m/%y").date()
            else:
                pay_date = False

            line_data = {
                'pay_period_date': pay_date,
                'insurable_earning': row.get('Insurable Earning'),
                'insurable_hour': row.get('Insurable Hour'),
            }

            lines.append((0, 0, line_data))

        active_ids = self.env.context.get('active_ids', [])
        employees = self.env["hr.employee"].browse(active_ids)

        employees.write({
            'roe_paycycle_ids': lines,
        })



    def action_download_template(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Report')

        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        # Headers
        headers = [
            'Pay Period Ending Date',
            'Insurable Earning',
            'Insurable Hour'
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Optional: set column width
        sheet.set_column(0, 2, 25)

        workbook.close()
        output.seek(0)

        file_data = output.read()

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Insurable_Report.xlsx',
            'type': 'binary',
            'raw': file_data,  # Odoo 20: `datas` was removed from ir.attachment
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

