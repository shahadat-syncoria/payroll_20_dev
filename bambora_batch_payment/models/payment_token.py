# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    bambora_profile = fields.Char()
    bambora_token = fields.Char()
    bambora_token_type = fields.Selection(
        string="Token Type",
        selection=[("temporary", "Temporary"), ("permanent", "Permanent")],
    )
    code = fields.Selection(
        string="Provider", related="provider_id.code", readonly=False
    )
    # save_token = fields.Selection(string="Save Cards", related="provider_id.save_token", readonly=False)
    bamboraeft_tran_type = fields.Selection(
        string="Transaction Type", selection=[("bank", "Bank"), ("card", "Card")]
    )
    partner_bank_id = fields.Many2one(
        string="Partner Bank",
        comodel_name="res.partner.bank",
        ondelete="restrict",
    )

    #=== BUSINESS METHODS ===#

    def _handle_archiving(self):
        """ Override of payment (Odoo 20 replaces `_handle_deactivation_request`).

        Bambora has no API call to remove a saved token, archiving is only done in Odoo.

        :return: None
        """
        super()._handle_archiving()
