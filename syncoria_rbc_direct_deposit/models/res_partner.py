from odoo import fields,models,api,_
from odoo.exceptions import UserError


class ResPartnerRBC(models.Model):
    _inherit = 'res.partner'

    rbc_client_number = fields.Char("RBC Assigned Client Number")

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    rbc_bank_transit_no = fields.Char(
        string="Bank Transit No",
    )