from ast import literal_eval

from odoo import fields, models,api, _

def day_selection(self):
    """
    Never change this helper function !!!!!!!!!
    It has impact in database .
    """
    day = 1
    day_list = []
    while day != 32:
        day_list.append((str(day), str(day)))
        day += 1
    return day_list

class PayrollResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    reminder_recipient_ids = fields.Many2many('res.partner', string='Reminder Recipient',)
    reminder_days_before_payroll = fields.Selection(
        day_selection,
        store=True,
        default='1',
        config_parameter='syncoria_can_payroll.reminder_days_before_payroll'
    )
    base_url = fields.Char(string='API Base URL',store=True,config_parameter='syncoria_can_payroll.base_url')
    token = fields.Char(string='Authentication Token', store=True,config_parameter='syncoria_can_payroll.token')

    attendance_manual_input= fields.Boolean(store=True,config_parameter='syncoria_can_payroll.attendance_manual_input')
    overtime_manual_input= fields.Boolean(store=True,config_parameter='syncoria_can_payroll.overtime_manual_input')

    @api.onchange("attendance_manual_input")
    def install_syncoria_payroll_helper(self):
        for record in self:
            if record.attendance_manual_input:
                module = self.env['ir.module.module'].search([('name', '=', 'syncoria_payroll_helper')], limit=1)
                if module.state != 'installed':
                    module.button_immediate_install()
                record.attendance_manual_input = True
            else:
                module = self.env['ir.module.module'].search([('name', '=', 'syncoria_payroll_helper')], limit=1)
                if module.state == 'installed':
                    module.button_immediate_uninstall()
                record.attendance_manual_input = False
    def set_values(self):
        res = super(PayrollResConfigSettings,self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('syncoria_can_payroll.reminder_recipient_ids',self.reminder_recipient_ids.ids)
        # return res

    @api.model
    def get_values(self):
        res = super(PayrollResConfigSettings,self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        reminder_recipient_ids = ICPSudo.get_param('syncoria_can_payroll.reminder_recipient_ids')
        if reminder_recipient_ids:
            res.update(
                reminder_recipient_ids=[(6,0,literal_eval(reminder_recipient_ids))]
            )
        return res




