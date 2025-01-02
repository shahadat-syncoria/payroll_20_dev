
from odoo import fields, models, _, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _reconcile_payments(self, to_process, edit_mode=False):
        res = super()._reconcile_payments(to_process, edit_mode=edit_mode)
        if self.env.context.get('hr_payroll_payment_register'):
            for vals in to_process:
                payslip = vals['to_reconcile'].move_id.payslip_ids
                # payslip = self.env['hr.payslip'].browse(self.env.context['hr_payroll_payment_register'])
                payslip.irregular_payment_paid()
        return res