
from odoo import api, fields, models


class ReportPayrollEarning(models.AbstractModel):
    _name = 'report.syncoria_can_payroll.report_payroll_earning'
    _description = "Payroll Earning"

    @api.model
    def _get_report_values(self, docids, data=None):
        data['currency_id'] = self.env.company.currency_id.symbol
        return {
            'doc_ids' : docids,
            'data' : data,
        }
