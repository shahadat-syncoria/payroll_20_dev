from odoo import fields,models,api


class AttendanceOvertimeStore(models.Model):
    _name = 'hr.attendance.overtime.store'
    _description = 'HR Attendance Overtime Store'


    # payslip_state=fields.Selection([('allocated','Allocated'),('not_allocated','Not Allocated')],default="not_allocated", required=True)
    employee_id = fields.Many2one(
        'hr.employee', string="Employee",required=True, ondelete='cascade', index=True)
    # pay_period=fields.Char("Pay period")
    payment_pay_period = fields.Many2one("paycycle.period", string="Payment Period")
    company_id = fields.Many2one(related='employee_id.company_id')
    year = fields.Integer(string="Year")

    date = fields.Date(string='Day')
    duration_store = fields.Float(string='Extra Hours Stored', default=0.0, required=True)
    duration_taken = fields.Float(string='Extra Hours Taken', default=0.0, required=True)
    duration_remaining = fields.Float(string='Extra Hours Remaining', default=0.0, compute='_compute_remaining_amount',required=True)
    amount_taken = fields.Float(string='Extra Amount Taken', default=0.0, required=True)
    amount = fields.Float(string='Amount')
    remaining_amount = fields.Float(string='Remaining Amount',default=0.0,compute='_compute_remaining_amount')
    overtime_rate = fields.Float(string='Overtime Rate')
    payslip_ids = fields.Many2many('hr.payslip', string='Payslips')
    need_to_payout = fields.Float(string='Need to Payout',default=0.0)
    is_need_payout_paid = fields.Boolean(string='Is Need Payout Paid',default=False)

    # @api.depends('amount_taken')
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount =  max(record.amount - record.amount_taken,0)
            record.duration_remaining =  max(record.duration_store - record.duration_taken,0)




    def action_allocate_extra_hour(self):
        contract_domain = [('contract_ids.state', 'in', ('open',)),
                           ('company_id', '=', self.env.company.id),
                           ]
        employees = self.env['hr.employee'].search(contract_domain)




        for employee in employees:
            # Overtime rate and amount calculation
            overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
                'can_overtime_pay_percent', raise_if_not_found=False)
            current_hourly_rate = self.payslip_ids[0].fixed_wage_hourly_rate
            overtime_hour_rate = (current_hourly_rate * (overtime_pay_percent / 100))

            print("Employee=>"+employee.name)
            paycycle_period_ids=employee.version_id.salary_pay_cycle.paycycle_period_ids.filtered(lambda x: fields.Date.today() > x.start_date )
            # self.search([('employee_id', '=', employee.id)]).duration_store = 0.0
            for paycyle in paycycle_period_ids:

                attendance_hour = sum(self.env["hr.attendance"].search([('employee_id', '=', employee.id),
                       ('check_in', '<=', paycyle.end_date),
                       ('check_out', '>=', paycyle.start_date)]).mapped("worked_hours"))
                pay_period = self.search([("payment_pay_period","=",paycyle.id),('employee_id', '=', employee.id)])
                need_to_pay = 0.0
                overtime_banked_hour_after_capped = 0.0
                real_overtime_hour = max(attendance_hour - 88, 0)
                if employee.total_stored_overtime > 44:
                    need_to_pay = real_overtime_hour
                else:
                    remaining_capped_amount_can_be_stored = 44 - employee.total_stored_overtime
                    if real_overtime_hour > remaining_capped_amount_can_be_stored :
                        overtime_banked_hour_after_capped = remaining_capped_amount_can_be_stored
                        need_to_pay = real_overtime_hour - remaining_capped_amount_can_be_stored
                    else:
                        overtime_banked_hour_after_capped = real_overtime_hour


                if not pay_period:
                    self.sudo().create({
                        'employee_id': employee.id,
                        'date': paycyle.start_date,
                        'payment_pay_period': paycyle.id,
                        'duration_store':  overtime_banked_hour_after_capped,
                        'duration_remaining':  overtime_banked_hour_after_capped,
                        'overtime_rate':  overtime_hour_rate,
                        'amount': overtime_banked_hour_after_capped * overtime_hour_rate,
                        'need_to_payout': need_to_pay
                    })
                else:
                    for record in pay_period.filtered(lambda r: not r.is_need_payout_paid):
                        record.write({
                            'duration_store': overtime_banked_hour_after_capped,
                            'amount': overtime_banked_hour_after_capped * overtime_hour_rate,
                            'need_to_payout': need_to_pay
                        })
                employee._compute_total_store_overtime()

    def open_payslip_action(self):
        """ Opens the payslip action window """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslip',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.payslip_ids.ids)],
        }


