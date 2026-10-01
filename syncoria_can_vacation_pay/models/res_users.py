from odoo import fields,models,api,_
from odoo.exceptions import UserError


class InheritedResUser(models.Model):
    _inherit = 'res.users'

    ytd_vac_pay_amount = fields.Float("Remaining Vacation Pay Amount",related="employee_id.ytd_vac_pay_amount",related_sudo=False)

    # v20: SELF_READABLE_FIELDS / SELF_WRITEABLE_FIELDS no longer exist (fields are readable by the user;
    # writing is governed by the `user_writeable` field parameter). This related field is read-only anyway.

    def action_view_employee_vacation_pay(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vacation Pay Request',
            'res_model': 'hr.vacation.pay',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'search_default_employee_id': self.employee_id.id if self.employee_id else False
            },

        }


