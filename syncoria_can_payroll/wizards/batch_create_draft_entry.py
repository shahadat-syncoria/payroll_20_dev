from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz
import base64
import io
import pandas as pd

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class SyncoriaCreateDraftWizard(models.TransientModel):
    _name = "hr.payslip.create.draft.wizard"
    _description = "HR Employee Create Draft Wizard"

    @api.model
    def _get_default_attendance_hours(self,hr_payslip_run,employee_id):
        if not employee_id.version_id.is_hourly:
            return (hr_payslip_run.date_end - hr_payslip_run.date_start).days *employee_id.version_id.standard_calendar_id.hours_per_day
        else:
            return 0.0

    def _get_payslip_run_id(self):
        context = self.env.context
        if 'active_model' in context and context.get('active_model') == 'hr.payslip.run':
            hr_payslip_run = self.env['hr.payslip.run'].browse(context.get('active_id'))
            return hr_payslip_run


    def _get_payslips(self):

        hr_payslip_run = self._get_payslip_run_id()
        vac_pay = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay')
        commission = self.env.ref('syncoria_can_irregular_payment.input_ca_commission')
        bonus = self.env.ref('syncoria_can_irregular_payment.input_ca_bonus_pay')
        retro = self.env.ref('syncoria_can_irregular_payment.input_ca_retro_pay')
        rec = []
        for payslip in hr_payslip_run.slip_ids:
            rec.append((0,0,{
                "slip_id" : payslip.id,
                "employee_id": payslip.employee_id,
                "struct_id":payslip.struct_id,
                "attendance_hours": payslip.worked_days_line_ids.filtered(lambda x: x.code == "WORK100").number_of_hours or
                                    payslip.worked_days_line_ids.filtered(lambda x: x.code == "TIMESHEET_WORK100").number_of_hours,
                "overtime_hours" : payslip.worked_days_line_ids.filtered(lambda x: x.code == "CAN_OVERTIME").number_of_hours,
                "stat_overtime_hours" : payslip.worked_days_line_ids.filtered(lambda x: x.code == "CAN_STAT_OVERTIME").number_of_hours,
                "payout_vacation_pay_paycycle":True if payslip.payout_vacation_pay_paycycle else False,
                "ytd_vac_pay_amount" : payslip.ytd_vac_pay_amount,
                "vac_pay" : payslip.input_line_ids.filtered(lambda x: x.code == vac_pay.code).amount,
                "commission" : payslip.input_line_ids.filtered(lambda x: x.code == commission.code).amount,
                "bonus" : payslip.input_line_ids.filtered(lambda x: x.code == bonus.code).amount,
                "retro" : payslip.input_line_ids.filtered(lambda x: x.code == retro.code).amount,
            }))
        # return [(0,0,{"employee_id": employee.id}) for employee in self.env['hr.employee'].search(contract_domain)]
        return rec

    is_bulk_upload = fields.Boolean("Bulk Upload", default=True)
    upload_file = fields.Binary("Excel File")
    upload_filename = fields.Char(readonly=True)

    draft_line_ids = fields.One2many("hr.employee.manual.input.line", 'create_draft_id', default=lambda self: self._get_payslips())

    def action_generate_draft_payslips(self):
        payslip_run_id = self._get_payslip_run_id()
        for payslip in payslip_run_id.slip_ids:
            payslip
        payslip_run_id.action_validate()

    def compute_sheet(self):

        payslip_run_id = self._get_payslip_run_id()

        # Recompute the entire payslip run if needed
        for payslip in payslip_run_id.slip_ids:
            payslip.compute_workdays_manual_input(self.draft_line_ids)
            payslip.compute_sheet()

    def action_download_template(self):
        self.ensure_one()
        payslips = self._get_payslips()
        if not payslips:
            raise UserError(_("No payslips available to generate template."))

        # Collect input codes from structures
        input_codes = []
        structures = []
        for line in payslips:
            if line[2]["struct_id"] not in structures:
                structures.append(line[2]["struct_id"])

        for structs in structures:
            if structs.input_line_type_ids:
                input_codes += [input.code for input in structs.input_line_type_ids]

        # Define columns
        columns = [   "Slip ID",
                      "Employee Name",
                  ] + [field for field in input_codes]

        # Build rows
        rows = []
        for line in payslips:
            row = [
                line[2]["slip_id"],
                line[2]["employee_id"].name,
            ]
            # Add input codes (default 0.0 if missing)
            for field in input_codes:
                row.append(getattr(line, field, 0.0))
            rows.append(row)

        # DataFrame
        df = pd.DataFrame(rows, columns=columns)

        # Write to Excel with formatting
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Template")
            workbook = writer.book
            worksheet = writer.sheets["Template"]

            # Define formats
            text_format = workbook.add_format({'align': 'left'})
            number_format = workbook.add_format({'num_format': '0.00', 'align': 'right'})

            # Apply formats by column
            worksheet.set_column(0, 0, 25, text_format)  # Employee Name column
            worksheet.set_column(1, len(columns) - 1, 15, number_format)  # All numeric columns

        output.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': 'Payslip_Bulk_Template.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_process_upload_to_slips(self):
        self.ensure_one()

        if not self.upload_file:
            raise UserError("Please upload an Excel file first.")

        try:
            file_content = base64.b64decode(self.upload_file)
            df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            raise UserError(f"Failed to read Excel file: {str(e)}")


        # missing_columns = [col for col in required_columns if col not in df.columns]
        # if missing_columns:
        #     raise UserError(f"Missing required columns in Excel: {', '.join(missing_columns)}")

        other_input_columns = [col for col in df.columns ]

        hr_input_obj = self.env['hr.payslip.input']

        for index, row in df.iterrows():
            slip_id = row["Slip ID"]
            slip = self._get_payslip_run_id().slip_ids.filtered(lambda s: s.id == slip_id)
            if not slip:
                continue  # Skip rows with no matching employee/payslip


            for field in other_input_columns:
                amount = row.get(field, 0.0)
                input_line = slip.input_line_ids.filtered(lambda l: l.code == field)
                if input_line:
                    input_line.amount = amount
                else:
                    # Create a new input line if it exists in hr.payslip.input.type
                    input_type = self.env['hr.payslip.input.type'].search([('code', '=', field)], limit=1)
                    if input_type and amount > 0.0 :
                        hr_input_obj.create({
                            "payslip_id": slip.id,
                            "input_type_id": input_type.id,
                            "amount": amount,
                            "code": field,
                        })
        self.compute_sheet()


        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }




