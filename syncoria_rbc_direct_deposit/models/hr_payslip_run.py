
from odoo import api, fields, models





class PayrollHrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    direct_deposit_txt = fields.Binary(
        string='Direct deposit',
        help="Export .txt file related to this payslip",
        readonly=True)
    direct_deposit_txt_filename = fields.Char(readonly=True)
    direct_deposit_txt_date = fields.Date(readonly=True)

    def action_txt_report(self, export_format='txt'):
        self.ensure_one()
        self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.slip_ids.ids,
            'payslip_run_id': self.id,
            'export_format': export_format
        }).generate_txt_payment_report()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=hr.payslip.run&id={self.id}&field=direct_deposit_txt&download=true&filename={self.direct_deposit_txt_filename}',
            'target': 'self',
        }