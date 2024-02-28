from odoo import api, fields, models, _
from io import BytesIO,StringIO
import base64
# import StringIO
import xlrd
class SyncoriaHrEmployeeManualWizardOvertime(models.TransientModel):
    _inherit = "hr.payslip.employee.manual.wizard"
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)

    def import_data(self):
        import binascii

        def is_xls_file(binary_data):
            xls_magic_number = b'D0CF11E0A1B11AE1'
            file_signature = binascii.hexlify(binary_data[:8]).upper()

            return file_signature == xls_magic_number

        if is_xls_file(self.file):
            print("The file is an Excel (.xls) file.")
        else:
            print("The file is not an Excel (.xls) file.")
        file_data = base64.b64decode(self.file)
        workbook = xlrd.open_workbook(file_contents=file_data)
        sheet = workbook.sheet_by_index(0)
        for rx in range(sheet.nrows):
            print(sheet.row(rx))
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': "hr.payslip.employee.manual.wizard",
            'target': 'new',
            'res_id': self.id
        }


class SyncoriaHrEmployeeManualInputLineOvertime(models.TransientModel):
    _inherit = "hr.employee.manual.input.line"

    overtime_hours = fields.Float(string="Overtime Number of Hours")
    stat_overtime_hours = fields.Float(string="Statutory Overtime Number of Hours")
