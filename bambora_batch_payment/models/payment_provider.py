###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
# pylint: disable=logging-not-lazy

import base64
import logging
import pprint
import random
import string

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.service import common

_logger = logging.getLogger(__name__)
version_info = common.exp_version()
server_serie = version_info.get("server_serie")

BATCH_API = "https://api.na.bambora.com/v1"
REPORT_API = "https://api.na.bambora.com/scripts/reporting/report.aspx"
PROFILE_URL = "https://api.na.bambora.com/v1/profiles"
INVOICE_MOVE_TYPES = {
    "entry": "Journal Entry",
    "out_invoice": "Customer Invoice",
    "out_refund": "Customer Credit Note",
    "in_invoice": "Vendor Bill",
    "in_refund": "Vendor Credit Note",
    "out_receipt": "Sales Receipt",
    "in_receipt": "Purchase Receipt",
}


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


def get_authorization(merchant_id, api_key):
    message = str(merchant_id + ":" + api_key).strip()
    base64_bytes = base64.b64encode(message.encode("ascii"))
    base64_message = base64_bytes.decode("ascii")
    return base64_message


def get_headers(merchant_id, api_key):
    headers = {
        "Authorization": "Passcode " + get_authorization(merchant_id, api_key),
        "Content-Type": "application/json",
    }
    return headers


def get_comment(self):
    comments = {
        "error": "Error %s ",
        "warning": "Build had issues",
        "failed": "Build failed",
    }
    return comments[self.type]


class ProviderBamboraEft(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("bamboraeft", _("Bambora EFT"))],
        ondelete={"bamboraeft": "set default"},
    )
    bamboraeft_merchant_id = fields.Char(
        string="Merchant ID", required_if_code="bamboraeft"
    )
    bamboraeft_batch_api = fields.Char(
        string="Batch API", required_if_code="bamboraeft"
    )
    bamboraeft_report_api = fields.Char(
        string="Report API", required_if_code="bamboraeft"
    )
    bamboraeft_transaction_type = fields.Selection(
        string="Transaction Type",
        selection=[("E", "EFT"), ("A", "ACH")],
        default="E",
        required_if_code="bamboraeft",
    )
    bamboraeft_create_profile = fields.Boolean(
        string="Create Profile",
    )
    bamboraeft_payment_api = fields.Char(
        string="Payment API", required_if_code="bamboraeft"
    )
    bamboraeft_profile_api = fields.Char(
        string="Profile API", required_if_code="bamboraeft"
    )
    bamboraeft_report_api_version = fields.Selection(
        string="Report Api Version",
        selection=[("2.0", "2.0")],
        default="2.0",
        required_if_code="bamboraeft",
    )
    bamboraeft_vendor_journal_id = fields.Many2one(
        "account.journal",
        "Vendor Payment Journal",
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        help="""Journal where the successful Vendor transactions will be posted""",
    )
    bambora_record_interval = fields.Integer(
        "Cron Record Interval",
        default=4000,
        readonly=True,
        help="Amount of record handle per cron request.",
    )
    debug_logging = fields.Boolean(help="Log requests in order to ease debugging")
    bamboraeft_dynamic_desc = fields.Char(string="Dynamice Descriptor")
    partner_ids = fields.Many2many("res.partner", string="Add contacts to notify..")
    bamboraeft_tran_type = fields.Selection(
        string="Bambora Transaction Type",
        selection=[("bank", "Bank"), ("card", "Card")],
    )
    batches_count = fields.Integer(string="Batch Count", compute="_compute_batches")

    test_batch = fields.Char(string="Test")

    # def action_toggle_is_published(self):
    #     res = super(ProviderBamboraEft,self).action_toggle_is_published()
    #     if self.code == 'bamboraeft':
    #         if self.is_published:
    #             self.is_published = False
    def write(self, vals):
        res = super(ProviderBamboraEft, self).write(vals)
        if self.code == 'bamboraeft':
            if self.is_published:
                self.is_published = False

        return res


    # === BUSINESS METHODS ===#

    # @api.model
    # def _is_tokenization_required(self, code=None, **kwargs):
    #     """ Override of payment to hide the "Save my payment details" input in checkout forms.
    #
    #     :param str code: The code of the provider handling the transaction
    #     :return: Whether the code is SEPA
    #     :rtype: bool
    #     """
    #     res = super()._is_tokenization_required(code=code, **kwargs)
    #     if code != 'bamboraeft':
    #         return res
    #
    #     return True



    def _bambora_make_request(self, payload=None, token=None):
        """Make a request to Adyen API at the specified endpoint.

        Note: self.ensure_one()
        :param dict payload: The payload of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        self.ensure_one()
        _logger.info(">>>>>>>>>>>>payload %s" % (pprint.pformat(payload)))
        tx_sudo = self.env["payment.transaction"].sudo().browse([payload.get("tx_id")])
        if tx_sudo:
            if not tx_sudo.partner_id.country_id or not tx_sudo.partner_country_id:
                raise ValidationError(
                    _(
                        "BamboraEFT: "
                        + _(
                            "Please add country for this customer. Country Field cannot be empty for Bambora EFT/ACH "
                            "Payment! "
                        )
                    )
                )
            if tx_sudo.provider_id.bamboraeft_tran_type == "bank":
                response = tx_sudo.action_register_bambora_batch_payment(
                    data=payload, token=token
                )
            if tx_sudo.provider_id.bamboraeft_tran_type == "card":
                response = tx_sudo.bamboraeft_card_payment_transaction(
                    data=payload, token=token
                )
        return response

    def action_view_batches(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Batch Tracking",
            "view_mode": "tree,form",
            "res_model": "batch.payment.tracking",
            "domain": [("provider_id", "=", self.id)],
            "context": "{'create': False}",
        }

    def _compute_batches(self):
        for record in self:
            record.batches_count = self.env["batch.payment.tracking"].search_count(
                [("provider_id", "=", self.id)]
            )

    def toggle_prod_environment(self):
        for rec in self:
            rec.prod_environment = not rec.prod_environment

    def toggle_debug(self):
        for rec in self:
            rec.debug_logging = not rec.debug_logging

    def _get_feature_support(self):
        # pylint: disable=super-with-arguments
        res = super(ProviderBamboraEft, self)._get_feature_support()
        res["tokenize"].append("bamboraeft")
        return res

    def bamboraeft_compute_fees(self, amount, currency_id, country_id):
        if not self.fees_active:
            return 0.0
        country = self.env["res.country"].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees


class Txbambora(models.Model):
    _inherit = "payment.transaction"

    bambora_auth_code = fields.Char("Auth Code")
    bambora_created = fields.Char("Bambora Created on")
    bambora_order_number = fields.Char("Order Number")
    bambora_txn_type = fields.Char("Transaction Type")
    bambora_payment_method = fields.Char("Payment Method")
    bambora_card_type = fields.Char("Card Type")
    bambora_last_four = fields.Char("Last Four")
    bambora_avs_result = fields.Char("AVS Result")
    bambora_cvd_result = fields.Char("CVD Result")
    bamboraeft_batch_id = fields.Many2one(
        string="Batch Id",
        comodel_name="batch.payment.tracking",
        ondelete="restrict",
    )
    bamboraeft_batch_mode = fields.Char(string="Batch Mode")
    bamboraeft_code = fields.Char(string="Code")
    bamboraeft_message = fields.Char(string="EFT Message")
    bamboraeft_process_date = fields.Char(string="Process date")
    bamboraeft_process_time_zone = fields.Char(string="Process Timezone")


