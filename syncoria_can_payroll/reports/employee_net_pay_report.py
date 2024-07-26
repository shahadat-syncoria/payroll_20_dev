
from odoo import api, fields, models


class ReportEmployeeNetPay(models.AbstractModel):
    _name = 'report.syncoria_can_payroll.report_employee_net_pay'
    _description = "Employee Net Pay"

    @api.model
    def _get_report_values(self, docids, data=None):
        data['currency_id'] = self.env.company.currency_id.symbol
        return {
            'doc_ids' : docids,
            'data' : data,
        }
