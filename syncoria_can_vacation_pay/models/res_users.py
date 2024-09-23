from odoo import fields,models,api,_
from odoo.exceptions import UserError


class InheritedResUser(models.Model):
    _inherit = ['res.users']

    ytd_vac_pay_amount = fields.Float("Remaining Vacation Pay Amount",related="employee_id.ytd_vac_pay_amount",related_sudo=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['ytd_vac_pay_amount']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['ytd_vac_pay_amount']


