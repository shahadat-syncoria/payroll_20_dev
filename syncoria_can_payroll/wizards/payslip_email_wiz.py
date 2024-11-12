import datetime

from odoo import models, fields, api

class PayslipEmailWizard(models.TransientModel):
    _name = 'payslip.email.wizard'
    _description = 'Payslip Email Wizard'

    employee_ids = fields.Many2many('hr.employee',string="Employee")

    def default_get(self, fields):
        defaults = super(PayslipEmailWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            payslip_records = self.env['hr.payslip'].browse(active_ids)
            employee_ids = list(set(payslip_records.mapped('employee_id.id')))
            defaults['employee_ids'] = [(6, 0, employee_ids)]

        return defaults

    def action_send(self):
       pass

