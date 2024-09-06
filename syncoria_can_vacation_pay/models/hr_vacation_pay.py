# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.populate import compute


class HrVacationPay(models.Model):
    _name = 'hr.vacation.pay'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Syncoria Vacation Pay request"
    _rec_name = "name"

    def _get_default_employee(self):
        # if self.env.context.get('active_model') in (
        #         'hr.employee', 'hr.employee.public') and 'active_id' in self.env.context:
        #     return self.env.context.get('active_id')
        # elif self.env.context.get('active_model') == 'res.users' and 'active_id' in self.env.context:
        #     return self.env['res.users'].browse(self.env.context['active_id']).employee_id
        # if not self.env.user.has_group('hr_appraisal.group_hr_appraisal_user'):
        return self.env.user.employee_id

    def _get_default_remaining_vacation(self):
        return self._get_remaining_vacation_employee(self.env.user.employee_id)
    def _get_default_remaining_vacation_pay_amount(self):

        return self.env.user.employee_id.ytd_vac_pay_amount


    name = fields.Char(string='Reference', required=True, copy=False, default='Draft', readonly=True)
    date = fields.Date(string="Requested Date", required=True, default=fields.Date.today())
    employee_id = fields.Many2one('hr.employee', required=True, default=_get_default_employee)
    duration = fields.Float("Duration")
    vacation_remain = fields.Float('Remaining Vacation', store=True,compute='_compute_remaining_vacation_employee',default=_get_default_remaining_vacation)
    vacation_pay_amount_remaining =  fields.Float('Remaining Vacation Pay Amount', store=True,compute='_compute_remaining_vacation_pay_amount_employee',default=_get_default_remaining_vacation_pay_amount)
    vacation_pay_amount = fields.Float('Amount')
    payslip_id = fields.Many2one('hr.payslip')
    paid_date = fields.Date(related='payslip_id.paid_date')
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
    is_last_pay = fields.Boolean(default=False)
    description = fields.Text(string="Description")
    department_id = fields.Many2one(related="employee_id.department_id",string="Department", store=True)
    job_id = fields.Many2one(related="employee_id.job_id",string="Job")
    contract_id = fields.Many2one(related="employee_id.contract_id",string="Contract")
    vacation_type = fields.Selection([('time_wise',"Time Store"),('cash_wise',"Cash Store"),
                                      ],string="Vacation Type",default='cash_wise',compute='_compute_vacation_type',store=True)



    def _compute_vacation_type(self):
        for rec in self:
            if rec.state == 'draft':
                rec.vacation_type = self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type')



    # =========================
    @api.depends('employee_id')
    def _compute_remaining_vacation_pay_amount_employee(self):
        for rec in self:
            rec.vacation_pay_amount_remaining = rec.employee_id.ytd_vac_pay_amount


    def _get_remaining_vacation_employee(self,employee_id):
        if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
            vac_pay_by_employee = self.search([('employee_id', '=', employee_id.id)])
            vacation_leave_type = self.env['hr.leave.type'].sudo().search([('allow_vacation_pay', '=', True)])
            vac_remain = 0.0
            taken_vacation_leave = sum(vac_pay_by_employee.filtered(
                lambda x: x.state == 'validate').mapped('duration'))
            try:
                for vac_type in vacation_leave_type:
                    data = vac_type.get_allocation_data(employee_id)
                    if data.get(employee_id):
                        if data.get(employee_id)[0][1]:
                            vac_remain = data.get(employee_id)[0][1].get(
                                'virtual_remaining_leaves') - taken_vacation_leave
            except Exception as e:
                pass
        else:
            vac_remain= 0.0

        return vac_remain

    # =========================


    @api.constrains('is_last_pay')
    def _constrain_is_last_pay(self):
        for rec in self:
            if rec.is_last_pay:
                multi_last_pay = self.search_count([('employee_id','=',self.employee_id.id),('is_last_pay','=',True)])

                if multi_last_pay >1:
                    raise UserError("Already requested for last pay!!")

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Record can not be deleted without draft state."))
        super(HrVacationPay,self).unlink()

    @api.depends('employee_id')
    def _compute_remaining_vacation_employee(self):
        for vac in self:
            if self.env["ir.config_parameter"].sudo().get_param(
                    'syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
                vac.vacation_remain = vac._get_remaining_vacation_employee(vac.employee_id)


    def action_confirm(self):
        if self.env["ir.config_parameter"].sudo().get_param('syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
            if self.duration <= 0.0:
                raise UserError(_("Duration must be grater than zero!"))
            elif round(self.vacation_remain,2) < self.duration:
                raise UserError(_("Duration can not be greater than remaining days."))
            self.write({'state': 'confirm'})

        if self.vacation_type =='cash_wise':
            if self.vacation_pay_amount <= 0.0:
                raise UserError(_("Amount must be grater than zero!"))
            elif round(self.vacation_pay_amount_remaining,2) < self.vacation_pay_amount:
                raise UserError(_("Amount can not be greater than remaining Amount."))
            self.write({'state': 'confirm'})

        if self.name == 'Draft':
            self.name = self.env['ir.sequence'].next_by_code('hr.vacation.pay')


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
