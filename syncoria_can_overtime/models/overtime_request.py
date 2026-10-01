# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrOvertimePayRequest(models.Model):
    _name = 'hr.overtime.pay.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Syncoria Overtime Pay request"
    _rec_name = "name"

    def _get_default_employee(self):
        # if self.env.context.get('active_model') in (
        #         'hr.employee', 'hr.employee.public') and 'active_id' in self.env.context:
        #     return self.env.context.get('active_id')
        # elif self.env.context.get('active_model') == 'res.users' and 'active_id' in self.env.context:
        #     return self.env['res.users'].browse(self.env.context['active_id']).employee_id
        # if not self.env.user.has_group('hr_appraisal.group_hr_appraisal_user'):
        return self.env.user.employee_id

    # def _get_default_remaining_vacation(self):
    #     return self._get_remaining_vacation_employee(self.env.user.employee_id)
    # def _get_default_remaining_vacation_pay_amount(self):
    #
    #     return self.env.user.employee_id.ytd_vac_pay_amount


    name = fields.Char(string='Reference', required=True, copy=False, default='Draft', readonly=True)
    date = fields.Date(string="Requested Date", required=True, default=fields.Date.today())
    employee_id = fields.Many2one('hr.employee', required=True, default=_get_default_employee)
    duration = fields.Float("Duration")
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        # ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('paid', 'Paid'),
        ('cancel', 'Cancel')
    ], string='Status',  store=True, tracking=True, copy=False, readonly=False, default='draft'
    )
    description = fields.Text(string="Description")
    department_id = fields.Many2one(related="employee_id.department_id",string="Department", store=True)
    job_id = fields.Many2one(related="employee_id.job_id",string="Job")
    version_id = fields.Many2one(related="employee_id.version_id",string="Contract")


    remaining_overtime = fields.Float(string="Remaining Overtime",compute='_compute_remaining_overtime',help="Remaining Overtime")
    overtime_pay = fields.Float('Overtime Duration',help="Requested Overtime Pay")

    @api.depends('employee_id')
    def _compute_remaining_overtime(self):
        for rec in self:
            rec.employee_id._compute_total_store_overtime()
            rec.remaining_overtime = rec.employee_id.total_stored_overtime








    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Record can not be deleted without draft state."))
        return super(HrOvertimePayRequest,self).unlink()



    def action_confirm(self):
        if self.overtime_pay <= 0.0:
            raise UserError(_("Duration must be grater than zero!"))
        elif round(self.remaining_overtime, 2) < self.overtime_pay:
            raise UserError(_("Duration can not be greater than remaining duration."))
        self.write({'state': 'confirm'})
        if self.name == 'Draft':
            self.name = self.env['ir.sequence'].next_by_code('hr.overtime.pay.request')


    def action_approve(self):
        self.write({'state': 'validate','date':fields.Date.today()})

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
