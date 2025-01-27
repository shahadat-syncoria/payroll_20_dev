from datetime import datetime

from odoo import fields, models, _


class RemittanceSummaryInherit(models.TransientModel):
    _inherit = "remittance.summary.wizard"
    _description = "Remittance Summary Report"



    def _get_data(self):
        res = super(RemittanceSummaryInherit,self)._get_data()
        query = """
        SELECT
        COUNT(DISTINCT p.employee_id) AS employees_paid,
        SUM(CASE WHEN pl.code IN ('EI', 'CPP', 'FTAX', 'OTAX') THEN pl.amount ELSE 0 END) AS total_amount,
        SUM(CASE WHEN pl.code = 'CPP' THEN pl.amount ELSE 0 END) AS total_cpp,
        SUM(CASE WHEN pl.code = 'CPP2' THEN pl.amount ELSE 0 END) AS total_cpp2,
        SUM(CASE WHEN pl.code = 'EI' THEN pl.amount ELSE 0 END) AS total_ei,
        SUM(CASE WHEN pl.code = 'FTAX' THEN pl.amount ELSE 0 END) AS total_ftax,
        SUM(CASE WHEN pl.code = 'OTAX' THEN pl.amount ELSE 0 END) AS total_otax,
        SUM(CASE WHEN pl.code = 'GROSS' THEN pl.amount ELSE 0 END) AS total_gross
    FROM
        hr_payslip p
    JOIN
        hr_payslip_line pl ON pl.slip_id = p.id
    WHERE
        p.state = 'paid'
        AND (p.credit_note IS NULL OR p.credit_note = false)
        AND p.company_id = %s
        AND p.date_from >= '%s'
        AND p.date_to <= '%s'
       """ % (self.env.company.id, self.date_from, self.date_to)
        cr = self.env.cr
        cr.execute(query)
        res = cr.dictfetchall()
        return res
        # return data,total_hours

    def print_report(self):
        datas={
            'date_range': f"{self.date_from.strftime('%d/%m/%Y')} to {self.date_to.strftime('%d/%m/%Y')}",

            'payslips' :self._get_data()
        }


        return self.env.ref('syncoria_can_payroll.action_report_remitance_summary_wizard').report_action(self, data=datas)
