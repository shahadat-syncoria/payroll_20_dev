from odoo import fields, models, _


PAYGROUP = {
        'monthly': 'Monthly',
        'quarterly':'Quarterly',
        'semi-annually': 'Semi-annually',
        'annually': 'Annually',
        'weekly': 'Weekly',
        'bi-weekly': 'Bi-weekly',
        'bi-monthly': 'Bi-monthly',
}


class RoeEarningPerEmployee(models.TransientModel):
    _name = "roe.earning.wizard"
    _description = "ROE Earning Per Employee Report"

    date_from = fields.Date("From Date", default=fields.Date.today())
    date_to = fields.Date("To Date", default=fields.Date.today())
    employee_id = fields.Many2one('hr.employee')

    def _get_employee_payslip(self):
        employee_payslip_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ('state', '=', 'paid')])
        date_wise_employee_payslip_ids = employee_payslip_ids.filtered(
            lambda s: s.date_from >= self.date_from and s.date_to <= self.date_to)

        data = []
        sum_gross = 0.00
        total_hours = 0.00

        for index, line in enumerate(date_wise_employee_payslip_ids):
            details_gross_info = []
            for pay_line in line.line_ids:
                if pay_line.category_id.code == 'GROSS':
                    sum_gross += pay_line.total
                    details_gross_info.append({
                        "name": pay_line.name,
                        "total": pay_line.total,
                    })
            total_hours += line.sum_worked_hours
            data.append({

                'pay': index+1,
                'paycycle_date_from': f"{line.date_from}",
                'paycycle_date_to': f"{line.date_from}",
                'hours': line.sum_worked_hours,
                'Gross': sum_gross,
                "details": line.struct_id.name,
                "gross_details": details_gross_info,
            })
        return data,total_hours

    def print_report(self):
        # data = {
        #     "employee":self.employee_id
        # }
        payslip_datas,total_hour = self._get_employee_payslip()
        datas = {
            'employee_name': self.employee_id.name,
            'hire_date': self.employee_id.first_contract_date.strftime('%Y-%m-%d') if self.employee_id.version_id.date_end else None,
            'term_date': self.employee_id.version_id.date_end.strftime('%Y-%m-%d') if self.employee_id.version_id.date_end else None,
            'paygroup': PAYGROUP.get(f'{self.employee_id.version_id.structure_type_id.default_schedule_pay}'),
            'payslips': payslip_datas,
            'total_hours': total_hour

        }
        # data['form']['data'] = {
        #     'employee':self.employee_id}
        return self.env.ref('syncoria_can_payroll.action_report_roe_earning_wizard').report_action(self, data=datas)
