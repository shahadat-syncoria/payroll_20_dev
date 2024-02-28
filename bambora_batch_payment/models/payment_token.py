# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


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

    def _handle_deactivation_request(self):
        """ Override of payment to request request Adyen to delete the token.

        Note: self.ensure_one()

        :return: None
        """
        super()._handle_deactivation_request()
        if self.code != 'bamboraeft':
            return

        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'shopperReference': self.bambora_shopper_reference,
            'recurringDetailReference': self.provider_ref,
        }
        try:
            self.provider_id._adyen_make_request(
                url_field_name='adyen_recurring_api_url',
                endpoint='/disable',
                payload=data,
                method='POST'
            )
        except ValidationError:
            pass  # Deactivating the token in Odoo is more important than in Adyen

    def _handle_reactivation_request(self):
        """ Override of payment to raise an error informing that Adyen tokens cannot be restored.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the token is managed by Adyen
        """
        super()._handle_reactivation_request()
        if self.code != 'bamboraeft':
            return

        raise UserError(_("Saved payment methods cannot be restored once they have been deleted."))
