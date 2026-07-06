from odoo import api, models


class ReportWSIB(models.AbstractModel):
    _name = "report.syncoria_can_payroll.report_wsib"
    _description = "WSIB Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        data["currency_id"] = self.env.company.currency_id.symbol
        return {
            "doc_ids": docids,
            "data": data,
            **data,
        }
