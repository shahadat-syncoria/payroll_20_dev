from odoo import fields, models, api


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    default_pay_cycle = fields.Many2one('paycycle.config', string="Default Pay Cycle")

    @api.onchange('default_pay_cycle')
    def _onchage_schedule_pay(self):
        self.ensure_one()
        if self.default_pay_cycle.pay_cycle == '12':
            self.default_schedule_pay = 'monthly'

        elif self.default_pay_cycle.pay_cycle == '24':
            self.default_schedule_pay = 'semi-monthly'

        elif self.default_pay_cycle.pay_cycle == '26':
            self.default_schedule_pay = 'bi-weekly'
        elif self.default_pay_cycle.pay_cycle == '52':
            self.default_schedule_pay = 'weekly'

        if self.default_struct_id:
            self.default_struct_id.structure_pay_cycle = self.default_pay_cycle


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    structure_pay_cycle = fields.Many2one('paycycle.config', string="Pay cycle", )

    def write(self, vals):

        if 'structure_pay_cycle' in vals:
            struct_paycycle_id = self.env['paycycle.config'].browse(vals['structure_pay_cycle'])
            if struct_paycycle_id.pay_cycle == '12':
                self.schedule_pay = 'monthly'
            elif struct_paycycle_id.pay_cycle == '24':
                self.schedule_pay = 'bi-monthly'

            elif struct_paycycle_id.pay_cycle == '26':
                self.schedule_pay = 'bi-weekly'
            elif struct_paycycle_id.pay_cycle == '52':
                self.schedule_pay = 'weekly'
        return super(HrPayrollStructure, self).write(vals)
