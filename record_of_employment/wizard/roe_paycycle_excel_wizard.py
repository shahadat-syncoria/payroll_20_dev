from odoo import models, fields, api, _
import base64
import pandas as pd
from io import BytesIO

from odoo.exceptions import UserError,ValidationError

class ProductProcessingExcelWizard(models.TransientModel):
    _name = "roe.paycycle.excel.wizard"
    _description = "ROE Paycycle Excel Wizard"

    excel_file = fields.Binary(string="File", required=True)

    def button_process(self):
        try:
            data = base64.b64decode(self.excel_file)
            excel_data = pd.read_excel(BytesIO(data))  # Ensure skuCode is read as a string
        except Exception as e:
            raise ValidationError(_("Error reading the Excel file: %s" % str(e)))

        lines = []
        for index, row in excel_data.iterrows():
            line_data = {
                'pay_period_date' : row.get('Pay Period Ending Date'),
                'insurable_earning' : row.get('Insurable Earning'),
                'insurable_hour' : row.get('Insurable Hour'),
            }
            lines.append((0, 0, line_data))

        active_id =self.env.context.get('active_ids', [])
        employee = self.env["hr.employee"].browse(active_id)
        employee.write({
            'roe_paycycle_ids': lines,

        })