from odoo import fields,models,api,_
from odoo.exceptions import UserError


class ResPartnerRBC(models.Model):
    _inherit = 'res.partner'

    rbc_client_number = fields.Char("RBC Assigned Client Number")

    @api.constrains('rbc_client_number')
    def _check_rbc_client_number(self):
        for rec in self:
            if len(rec.rbc_client_number) !=10:
                raise UserError(_("RBC Client Number must be 10 characters long"))


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    rbc_bank_transit_no = fields.Char(
        string="Bank Transit No",
    )