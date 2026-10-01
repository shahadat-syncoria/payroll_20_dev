from odoo import fields,models,api,_
from odoo.exceptions import UserError


class ResPartnerRBC(models.Model):
    _inherit = 'res.partner'

    rbc_client_number = fields.Char("RBC Assigned Client Number")

    @api.constrains('rbc_client_number')
    def _check_rbc_client_number(self):
        for rec in self:
            if rec.rbc_client_number and len(rec.rbc_client_number) !=10:
                raise UserError(_("RBC Client Number must be 10 characters long"))


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    rbc_bank_transit_no = fields.Char(
        string="RBC Financial Institution Branch Number",
    )

    @api.constrains('rbc_bank_transit_no')
    def _check_rbc_bank_transit_no(self):
        for rec in self:
            if rec.rbc_bank_transit_no and len(rec.rbc_bank_transit_no) != 5:
                raise UserError(_("RBC Financial Institution Branch Number must be 5 characters long"))