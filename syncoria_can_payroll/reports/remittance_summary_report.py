# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReportRemitanceSummary(models.AbstractModel):
    _name = 'report.syncoria_can_payroll.report_remittance_summary'
    _description = "Remittance Summary"

    @api.model
    def _get_report_values(self, docids, data=None):
        data['currency_id'] = self.env.company.currency_id.symbol
        return {
            'doc_ids' : docids,
            'data' : data,
        }
