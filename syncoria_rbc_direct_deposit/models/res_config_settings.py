from odoo import fields, models
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'

    production = fields.Boolean(
        string="Production",
        help="Enable this option if the environment is production.")
    fcn_history = fields.Char(default="")

    def _generate_fcn(self):
        # TEST mode
        # if not self.company_id.production:
        #     return "TEST"

        # PRODUCTION MODE
        # last 9 FCNs stored as comma-separated text: "0001,0002,..."
        history_raw = self.env.company.fcn_history or ""
        history = history_raw.split(",")[-99:] if history_raw else []

        # Convert to int list
        recent = set(int(x) for x in history if x.isdigit())

        # Generate new FCN from 00–99
        for i in range(1,9999):
            if i not in recent:
                new_fcn = f"{i:04d}"
                # Save back to company history
                updated = (history + [new_fcn])[-99:]
                self.env.company.fcn_history = ",".join(updated)
                return new_fcn

        raise ValidationError("No available FCN (ran out of 10,000 numbers).")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    production = fields.Boolean(
        related='company_id.production',
        string="production",
        readonly=False,
        help="Enable this option if the environment is production.")

