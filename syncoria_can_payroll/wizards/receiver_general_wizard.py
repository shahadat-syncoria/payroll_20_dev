from odoo import fields, models, _

PAYGROUP = [
    ('monthly','Monthly'),
    ('quarterly','Quarterly'),
    ('semi-annually','Semi-annually'),
    ('annually','Annually'),
    ('weekly','Weekly'),
    ('bi-weekly', 'Semi-weekly'),
    ('bi-monthly','Semi-monthly'),
]


class RemittanceSummary(models.TransientModel):
    _name = "receiver.general.wizard"
    _description = "Receiver General Report"

    date_from = fields.Date("From Date", default=fields.Date.today())
    date_to = fields.Date("To Date", default=fields.Date.today())
    paygroup = fields.Selection(PAYGROUP,default='bi-monthly')

    def _get_data(self):
        # FIXME: Convert this to raw sql for better performance

        payslip_ids = self.env['hr.payslip'].search(
            [('date_from','>=',self.date_from),('date_to','<=',self.date_to),('state', '=', 'paid')])
        total_cpp_employee = 0.0
        total_cpp_employer = 0.0
        total_ei_employee = 0.0
        total_ei_employer = 0.0
        total_gross = 0.0
        total_fed = 0.0
        total_prov = 0.0
        data= {}
        for pay in payslip_ids:
            for line in pay.line_ids:
                # if line.code == 'CPP_QPP_EA':
                #     canada_cpp_qpp_ern_amt += line.amount
                if line.code == 'CPP':
                    total_cpp_employee += line.amount
                elif line.code == 'CPP_EMPLOYER':
                    total_cpp_employer += line.amount
                elif line.category_id.code == 'GROSS':
                    total_gross += line.amount
                elif line.code == 'EI':
                    total_ei_employee += line.amount
                elif line.code == 'EI_EMPLOYER':
                    total_ei_employer += line.amount
                elif line.code == 'FTAX':
                    total_fed += line.amount
                elif line.code == 'OTAX':
                    total_prov += line.amount

            data.update({
                'total_cpp_employee': total_cpp_employee,
                'total_cpp_employer': total_cpp_employer,
                'total_ei_employee': total_ei_employee,
                'total_ei_employer': total_ei_employer,
                'total_gross': total_gross,
                'total_income_tax': total_fed+total_prov,
                'total_employee_paid': len(payslip_ids),
            })
        return data
        # return data,total_hours

    def print_report(self):
        datas = {
            "company_name":self.env.company.name,
            "paygroup": dict(self._fields['paygroup'].selection).get(self.paygroup),
            "date_to": self.date_to,
            "date_from": self.date_from,
            "cra_number": self.env.company.partner_id.employeer_cra_number,
        }
        datas['payslips'] = self._get_data()

        return self.env.ref('syncoria_can_payroll.action_report_rgr').report_action(self,data=datas)