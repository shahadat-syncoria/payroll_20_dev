# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrIrregularPayment(models.Model):
    _name = 'hr.irregular.pay'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Hr Irregular Payment"
    _rec_name = "name"

    def _get_available_contracts_domain(self):
        # return [
        #     ('version_id.state', 'in', ('open', 'close')),
        #     ('company_id', '=', self.env.company.id),
        #     ('version_id.date_start', '<=', self.date),
        #     '|',  # Logical OR operator
        #     ('version_id.date_end', '>=', self.date),
        #     ('version_id.date_end', '=', False)  # Handles empty end date
        # ]
        return [
            ('company_id', '=', self.env.company.id),
            ('contract_date_start', '<=', self.date),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', self.date),
            # ('date_version', '<=', date_end),
        ]

    def _get_employee_line(self):
        employee_line_list = [(0, 0, {
            'employee_id': employee_id.id,
        }) for employee_id in self.env['hr.employee'].search(self._get_available_contracts_domain())]
        return employee_line_list

    name = fields.Char(string='Reference', required=True, copy=False, default='Draft', readonly=True)
    description = fields.Text(string="Description", required=True, )
    date = fields.Date(string="Requested Date", required=True, default=fields.Date.today())

    line_ids = fields.One2many('employee.wise.irregular.pay', 'irr_pay_id', 'Employees', store=True,
                               default=lambda self: self._get_employee_line())
    payment_type = fields.Selection([
        ('bonus', 'Bonus'),
        ('retro', 'Retro Pay'),
        ('commission', 'Commission'),
    ], default='bonus', required=True, store=True)
    amount_type = fields.Selection([
        # ('percent','%'),
        ('fixed', 'Fixed'),
    ], default='fixed', required=True, store=True)
    amount = fields.Float("Amount", help="")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('validate', 'Approved'),
        ('paid', 'Paid'),
        ('cancel', 'Cancel')
    ], string='Status', store=True, tracking=True, copy=False, readonly=False, default='draft'
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    amount_cal_type = fields.Selection([
        ('global', 'Same amount for all'),
        ('employee_wise', 'Employee Wise Amount')
    ], string='Amount Calculation Type', store=True, )

    # Filters
    department_id = fields.Many2one('hr.department', string="Department")
    paycycle_ids = fields.Many2many('paycycle.config', string="Pay Cycle")


    @api.constrains("amount")
    def _amount_constrain(self):
        if self.amount_cal_type == 'global':
            if self.amount <= 0.0:
                raise UserError("Amount Must be Greater than zero!")

    @api.onchange('department_id','paycycle_ids',)
    def _onchange_department(self):
       for rec in self:
            domain = self._get_available_contracts_domain()
            if rec.department_id:
                domain += [('department_id', 'child_of', rec.department_id.id)]
            if rec.paycycle_ids:
                domain += [('version_id.salary_pay_cycle', 'in', rec.paycycle_ids.ids)]

            domain_wise_employee = self.env['hr.employee'].search(domain)
            rec.line_ids = [(6, 0, [])]
            employee_line_list = [(0, 0, {
                'employee_id': employee_id.id,
            }) for employee_id in domain_wise_employee]

            rec.line_ids = employee_line_list

    @api.onchange('amount_cal_type', 'amount')
    def _onchange_amount_cal_amount(self):
        self.ensure_one()
        if self.amount_cal_type == 'global':
            self.line_ids.amount = self.amount
        else:
            self.line_ids.amount = 0.0


    def unlink(self):
        if self.state != 'draft':
            raise UserError(_("Record can not be deleted without draft state."))
        super(HrIrregularPayment,self).unlink()

    def action_confirm(self):
        self.write({'state': 'to_approve'})
        if self.name == 'Draft':
            self.name = self.env['ir.sequence'].next_by_code('hr.irregular.pay')

    def action_approve(self):
        self.write({'state': 'validate','date': fields.Date.today()})


    def action_validate(self):
        self.write({'state': 'validate'})

    def action_refuse(self):
        self.write({'state': 'refuse'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_paid(self):
        self.write({'state': 'paid'})




class EmployeeWiseIrregularPay(models.Model):
    _name = 'employee.wise.irregular.pay'
    _description = "Employee Wise Irregular Pay"

    def _get_amount_default_value(self):
        return self.irr_pay_id.amount or 0.0

    def _get_available_contracts_domain(self):
        return [('version_ids.state', 'in', ('open', 'close')), ('company_id', '=', self.env.company.id)]

    irr_pay_id = fields.Many2one('hr.irregular.pay')
    employee_id = fields.Many2one('hr.employee',domain=lambda self:self._get_available_contracts_domain())
    amount = fields.Float("Amount", help="", default=lambda self: self._get_amount_default_value())
    pay_status = fields.Boolean('Status', default=False)

    @api.constrains("amount")
    def _amount_constrain(self):
        for rec in self:
            if rec.amount <= 0.0:
                raise UserError("Amount Must be Greater than zero!")
    def write(self, vals):
        res = super(EmployeeWiseIrregularPay, self).write(vals)
        if all(self.irr_pay_id.line_ids.mapped('pay_status')):
            self.irr_pay_id.write({
                'state': 'paid'
            })
        return res
