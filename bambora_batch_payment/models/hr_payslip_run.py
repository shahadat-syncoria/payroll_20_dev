from odoo import api,fields,models,_
from odoo.exceptions import UserError

class BamboraHrPayslipRun(models.Model):
    _inherit= 'hr.payslip.run'

    # state = fields.Selection([
    #     ('draft', 'New'),
    #     ('validated', 'Confirmed'),
    #     ('close', 'Done'),
    #     ('waiting', 'Bambora Waiting'),
    #     ('paid', 'Paid'),
    # ], string='Status', index=True, readonly=True, copy=False, default='draft', store=True,
    #     compute='_compute_state_change')
    is_bambora_deposite = fields.Boolean(string="Is bambora deposit?",default=False)


    def action_register_bambora_batch_payment(self):
        try:
            if self.slip_ids:
                payslip_ids = self.slip_ids.action_register_bambora_batch_payment()
                # self.write({
                #     'state':'waiting'
                # })
                self.is_bambora_deposite = True
                self.message_post(body=f"{fields.Datetime.now()}-Send for Bambora deposit")
        except Exception as e:
            raise UserError(_(f"Bank Deposit did not complete.\n Reason:{e}"))

    def print_deposit_report(self):
        return self.env.ref('bambora_batch_payment.action_report_deposit_summary_wizard').report_action(self)



