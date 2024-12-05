from odoo import models, fields, api

class PaycycleConfigUpdateWizard(models.TransientModel):
    _name = 'paycycle.config.update.wizard'
    _description = "Batch Update Paycycle Info"

    config_ids = fields.Many2many('paycycle.config',string="Payslip Config")

    def default_get(self, fields):
        defaults = super(PaycycleConfigUpdateWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            configs = self.env["paycycle.config"].search([("id", "in", active_ids)])
            defaults['config_ids'] = [(6, 0,configs.ids)]

        return defaults


    def update_payslip_config_info(self):
        for x in self.config_ids:
            line_obj = x.paycycle_period_year_slab_ids.filtered(lambda x: x.year == str(2024))
            if line_obj:
                continue
            if not line_obj:
                line_obj = self.env["paycycle.period.year.slab"].create(
                    {
                        "paycycle_config_id": x.id,
                        "year": str(2024),
                    }
                )
            for y in x.paycycle_period_ids:
                y.paycycle_year_slab_id = line_obj.id
                y.year = str(2024)


