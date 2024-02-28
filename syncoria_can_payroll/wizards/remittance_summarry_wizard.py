from odoo import fields, models, _

PAYGROUP = {
    'monthly': 'Monthly',
    'quarterly': 'Quarterly',
    'semi-annually': 'Semi-annually',
    'annually': 'Annually',
    'weekly': 'Weekly',
    'bi-weekly': 'Bi-weekly',
    'bi-monthly': 'Bi-monthly',
}


class RemittanceSummary(models.TransientModel):
    _name = "remittance.summary.wizard"
    _description = "Remittance Summary Report"

    date_from = fields.Date("From Date", default=fields.Date.today())
    date_to = fields.Date("To Date", default=fields.Date.today())

    def _get_data(self):
        query = """
        SELECT
-- 	p.id as id,
	p.paid_date AS pay_date,
    count(DISTINCT p.employee_id) AS employees_paid,
    SUM(CASE WHEN pl.code = 'EI' OR pl.code = 'CPP' OR pl.code = 'FTAX' OR pl.code = 'OTAX' THEN pl.amount ELSE 0 END) AS total_amount,
	SUM(CASE WHEN pl.code = 'GROSS' THEN pl.amount ELSE 0 END) AS total_gross
FROM
    hr_payslip p
JOIN
    hr_payslip_line pl ON pl.slip_id = p.id
where 
	p.state='paid'
	and (p.credit_note is NULL or p.credit_note = false)
	and p.company_id= %s
	and p.paid_date >= '%s'
	and p.paid_date <= '%s'

GROUP BY
-- p.id,
p.paid_date
ORDER BY
	p.paid_date
       """ % (self.env.company.id, self.date_from, self.date_to)
        cr = self.env.cr
        cr.execute(query)
        res = cr.dictfetchall()
        return res
        # return data,total_hours

    def print_report(self):
        datas={}
        datas['payslips'] = self._get_data()

        return self.env.ref('syncoria_can_payroll.action_report_remitance_summary_wizard').report_action(self, data=datas)
