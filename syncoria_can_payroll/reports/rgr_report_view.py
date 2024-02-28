# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReportGeneralReceiver(models.AbstractModel):
    _name = 'report.syncoria_can_payroll.report_rgr'
    _description = "General Receiver Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data['currency_id'] = self.env.company.currency_id.symbol
        return {
            'doc_ids' : docids,
            'data' : data,
        }
