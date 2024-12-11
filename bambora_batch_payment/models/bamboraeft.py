###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
#pylint: disable=logging-not-lazy

import base64
import csv
import datetime
import json
import logging
import os
import pprint
import random
import string
import urllib

import requests
from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.exceptions import UserError
from odoo.http import request
from odoo.service import common

from odoo.addons.payment import utils as payment_utils


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
        'error': 'Error %s ',
        'warning': 'Build had issues',
        'failed': 'Build failed'
    }
    return comments[self.type]

# def post_comment(self, comment):
#     self.post(comment, type=self.type)


class providerBamboraEft(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("bamboraeft", _("Bambora EFT"))],
        ondelete={"bamboraeft": "set default"},
    )
    bamboraeft_merchant_id = fields.Char(string="Merchant ID", required_if_code="bamboraeft")
    bamboraeft_batch_api = fields.Char(string="Batch API", required_if_code="bamboraeft")
    bamboraeft_report_api = fields.Char(string="Report API", required_if_code="bamboraeft")
    bamboraeft_transaction_type = fields.Selection(
        string="Transaction Type",
        selection=[("E", "EFT"), ("A", "ACH")],
        default="E",
        required_if_code="bamboraeft",
    )
    bamboraeft_create_profile = fields.Boolean(
        string="Create Profile",
    )
    bamboraeft_payment_api = fields.Char(string="Payment API", required_if_code="bamboraeft")
    bamboraeft_profile_api = fields.Char(string="Profile API", required_if_code="bamboraeft")
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
    bamboraeft_tran_type = fields.Selection(string="Bambora Transaction Type", selection=[("bank", "Bank"), ("card", "Card")])


    # @api.onchange("payment_flow")
    # def _onchange_payment_flow(self):
    #     for rec in self:
    #         if rec.code == "bamboraeft" and rec.payment_flow != "s2s":
    #             raise UserError(_("Bambora EFT cannot be configured with `Redirection to the provider website`."))

    batches_count = fields.Integer(string="Batch Count", compute="compute_batches")

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'bamboraeft').update({
            'allow_tokenization': 'full_only',
            'support_tokenization': True,
        })

    #=== BUSINESS METHODS ===#

    def _bambora_make_request(
        self, url_field_name, endpoint, endpoint_param=None, payload=None, method='POST'
    ):
        """ Make a request to Adyen API at the specified endpoint.

        Note: self.ensure_one()

        :param str url_field_name: The name of the field holding the base URL for the request
        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the provider reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(_base_url, _version, _endpoint):
            """ Build an API URL by appending the version and endpoint to a base URL.

            The final URL follows this pattern: `<_base>/V<_version>/<_endpoint>`.

            :param str _base_url: The base of the url prefixed with `https://`
            :param int _version: The version of the endpoint
            :param str _endpoint: The endpoint of the URL.
            :return: The final URL
            :rtype: str
            """
            _base = _base_url.rstrip('/')  # Remove potential trailing slash
            _endpoint = _endpoint.lstrip('/')  # Remove potential leading slash
            return f'{_base}/V{_version}/{_endpoint}'

        self.ensure_one()

        base_url = self[url_field_name]  # Restrict request URL to the stored API URL fields
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        url = _build_url(base_url, endpoint)
        headers = {'X-API-Key': self.adyen_api_key}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Adyen: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", url, payload, error.response.text
            )
            raise ValidationError("Adyen: " + _("The communication with the API failed."))
        return response.json()

    def bamboraeft_process(self, data):
        self.check_so_transactions(data)
        res_partner_bank = self.env["res.partner.bank"].sudo()
        res_partner = self.env["res.partner"].sudo()
        res_bank = self.env["res.bank"].sudo()
        partner = res_partner.search([("id", "=", int(data.get("partner_id")))])
        partner_name = ""
        if partner:
            partner_name = partner.name
            partner_name = partner_name.split(" ")[0] if partner_name else ""

        bank_id = self.check_bank_acc(res_partner_bank, res_partner, res_bank, partner, data)

        # Create a New Profile for Bank Account or Credit Card
        tran_type = "CARD" if data.get("bamboraTran") == "on" else "A/N"
        values = {}
        if data.get("bamboraTran") == "on":
            _logger.info("Payment by Card")
        else:
            _logger.info("Payment by Bank Number")
            values["partner_bank_id"] = bank_id.id

        comments = "Create Token for Customer-%s, %s" % (
            data.get("partner_id"),
            tran_type,
        )
        token_name = data.get("acc_number") if data.get("bamboraTran") != "on" else data.get("cc_number")
        token_name = (
            "***" + data.get("acc_number")[-4:] + " (EFT)"
            if data.get("bamboraTran") != "on"
            else data.get("cc_number")
        )
        values = {
            "bambora_token_type": "temporary",
            "bambora_token": data.get("token"),
            "code": "bamboraeft",
            "provider_id": int(data.get("provider_id")),
            "provider_ref": "bamboraeft",
            "partner_id": data.get("partner_id"),
            "name": token_name,
        }

        values["bamboraeft_tran_type"] = "card" if data.get("bamboraTran") == "on" else "bank"
        if self.bamboraeft_create_profile:
            pro_data = {
                "language": "en",
                "comments": comments,
                "bank_account": {
                    "bank_account_holder": data.get("acc_holder_name"),
                    "account_number": data.get("acc_number"),
                    "bank_account_type": data.get("bank_account_type"),
                    "institution_number": data.get("institution_number"),
                    "branch_number": data.get("branch_number"),
                },
            }

            _logger.info(pprint.pformat(data))
            headers = get_headers(data.get("bamboraeft_merchant_id"), data.get("bamboraeft_profile_api"))
            pro_res = requests.post(PROFILE_URL, data=json.dumps(pro_data), headers=headers)

            if self.debug_logging:
                _logger.info(
                    "\npro_res.status_code===>>> %d" % (pro_res.status_code)
                    + "\npro_res.status_code===>>> %s" % (pro_res.text)
                )

            self.process_response(pro_res, values, partner, bank_id, data, res_partner_bank)
        else:
            self.create_bank_account(partner, bank_id, data, res_partner_bank)

        payment_method = self.env["payment.token"].sudo().create(values)
        _logger.info(values)
        _logger.info(payment_method)
        return payment_method

    def action_view_batches(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Batch Tracking",
            "view_mode": "list,form",
            "res_model": "batch.payment.tracking",
            "domain": [("provider_id", "=", self.id)],
            "context": "{'create': False}",
        }

    def compute_batches(self):
        for record in self:
            record.batches_count = self.env["batch.payment.tracking"].search_count([("provider_id", "=", self.id)])

    def toggle_prod_environment(self):
        for rec in self:
            rec.prod_environment = not rec.prod_environment

    def toggle_debug(self):
        for rec in self:
            rec.debug_logging = not rec.debug_logging

    def _get_feature_support(self):
        # pylint: disable=super-with-arguments
        res = super(providerBamboraEft, self)._get_feature_support()
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

    def check_bank_acc(self, res_partner_bank, res_partner, res_bank, partner, data):
        bank_id = False
        if not data.get("bamboraTran") and data["acc_number"]:
            bank_account_id = res_partner_bank.search([("acc_number", "=", data["acc_number"])])
            if bank_account_id:
                msg = 'You cannot use this Account Number as it is already used. Please use a different account number!'
                raise UserError(_(msg))

        if partner and data.get("bank_name"):
            bank_id = res_bank.search([("name", "=", data.get("bank_name"))], limit=1)
            if not bank_id:
                bank_vals = {
                    "name": data.get("bank_name"),
                    "bic": data.get("institution_number"),
                }
                bank_id = res_bank.create(bank_vals)

        return bank_id

    @api.model
    def bamboraeft_s2s_form_process(self, data):
        res_partner_bank = self.env["res.partner.bank"].sudo()
        res_partner = self.env["res.partner"].sudo()
        res_bank = self.env["res.bank"].sudo()
        partner = res_partner.search([("id", "=", int(data.get("partner_id")))])
        partner_name = ""
        if partner:
            partner_name = partner.name
            partner_name = partner_name.split(" ")[0] if partner_name else ""

        bank_id = self.check_bank_acc(res_partner_bank, res_partner, res_bank, partner, data)

        # Create a New Profile for Bank Account or Credit Card
        tran_type = "CARD" if data.get("bamboraTran") == "on" else "A/N"
        values = {}
        if data.get("bamboraTran") == "on":
            _logger.info("Payment by Card")
        else:
            _logger.info("Payment by Bank Number")
            values["partner_bank_id"] = bank_id.id

        comments = "Create Token for Customer-%s, %s" % (
            data.get("partner_id"),
            tran_type,
        )
        token_name = data.get("acc_number") if data.get("bamboraTran") != "on" else data.get("cc_number")
        token_name = (
            "***" + data.get("acc_number")[-4:] + " (EFT)"
            if data.get("bamboraTran") != "on"
            else data.get("cc_number")
        )
        values = {
            "bambora_token_type": "temporary",
            "bambora_token": data.get("token"),
            "provider": "bamboraeft",
            "providerid": int(data.get("providerid")),
            "providerref": "bamboraeft",
            "partner_id": data.get("partner_id"),
            "name": token_name,
        }

        values["bamboraeft_tran_type"] = "card" if data.get("bamboraTran") == "on" else "bank"
        if self.bamboraeft_create_profile:
            pro_data = {
                "language": "en",
                "comments": comments,
                "bank_account": {
                    "bank_account_holder": data.get("acc_holder_name"),
                    "account_number": data.get("acc_number"),
                    "bank_account_type": data.get("bank_account_type"),
                    "institution_number": data.get("institution_number"),
                    "branch_number": data.get("branch_number"),
                },
            }

            _logger.info(pprint.pformat(data))
            headers = get_headers(data.get("bamboraeft_merchant_id"), data.get("bamboraeft_profile_api"))
            pro_res = requests.post(PROFILE_URL, data=json.dumps(pro_data), headers=headers)

            if self.debug_logging:
                _logger.info(
                    "\npro_res.status_code===>>> %d" % (pro_res.status_code)
                    + "\npro_res.status_code===>>> %s" % (pro_res.text)
                )

            self.process_response(pro_res, values, partner, bank_id, data, res_partner_bank)
        else:
            self.create_bank_account(partner, bank_id, data, res_partner_bank)

        payment_method = self.env["payment.token"].sudo().create(values)
        _logger.info(values)
        _logger.info(payment_method)
        return payment_method

    def create_bank_account(self, partner, bank_id, data, res_partner_bank):
        try:
            if partner and bank_id:
                partner_bank_id = partner.bank_ids.filtered(lambda c: c.acc_number == data["acc_number"])
                bank_account_vals = {}
                bank_account_vals["acc_holder_name"] = data["acc_holder_name"]
                bank_account_vals["acc_number"] = data["acc_number"]
                bank_account_vals["acc_type"] = "normal"
                bank_account_vals["bank_bic"] = data["institution_number"]
                bank_account_vals["bank_transit_no"] = data["branch_number"]
                bank_account_vals["partner_id"] = partner.id
                bank_account_vals["bank_id"] = bank_id.id
                partner_bank_id = (
                    res_partner_bank.create(bank_account_vals)
                    if not partner_bank_id
                    else partner_bank_id.write(bank_account_vals)
                )
            else:
                _logger.warning("Bank Name not provided")
        except Exception as e:
            msg ='Exceptions {}'.format(e.args)
            _logger.info(msg)

    def process_response(self, pro_res, values, partner, bank_id, data, res_partner_bank):
        if pro_res.status_code == 200:
            if pro_res.json().get("code") == 1:
                _logger.info("Bambora Profile successfully created")
                values["bambora_profile"] = pro_res.json().get("customer_code")
                values["bambora_token_type"] = "permanent"
                try:
                    # Create a Bank Account for the Customer
                    if partner and bank_id:
                        partner_bank_id = partner.bank_ids.filtered(lambda c: c.acc_number == data["acc_number"])
                        bank_account_vals = {}
                        bank_account_vals["acc_holder_name"] = data["acc_holder_name"]
                        bank_account_vals["acc_number"] = data["acc_number"]
                        bank_account_vals["acc_type"] = "normal"
                        bank_account_vals["partner_id"] = partner.id
                        bank_account_vals["bank_id"] = bank_id.id
                        bank_account_vals["bamboraeft_customer_code"] = pro_res.json().get("customer_code")
                        if not partner_bank_id:
                            partner_bank_id = res_partner_bank.create(bank_account_vals)
                    else:
                        _logger.warning("Bank Name not provided")
                except Exception as e:
                    _logger.warning("Exceptions" + str(e.args))

            else:
                _logger.warning("Customer Profile: Failure")
                message = pro_res.json().get("message")
                if message.get("details"):
                    if isinstance(message.get("details"), list):
                        for detail in message.get("details"):
                            message += "\n" + "Field Error: %s, Message: %s" % (
                                detail.get("field"),
                                detail.get("message"),
                            )

                raise ValidationError(_(message))
        else:
            message = pro_res.json().get("message")
            if pro_res.json().get("details"):
                if isinstance(pro_res.json().get("details"), list):
                    for detail in pro_res.json().get("details"):
                        message += "\n" + ",Field Error: %s, Message: %s" % (
                            detail.get("field"),
                            detail.get("message"),
                        )
            raise ValidationError(_(message))

        # if self.debug_logging:
        #     message="Status Code===>>> %s"%str(pro_res.status_code)
        #     message="Status Code===>>> %s"%str(pro_res.status_code)
        #     _logger.info(message)

    def check_so_transactions(self, data):
        exist_order = False
        if data:
            href = request.params.get("window_href") or request.httprequest.url or data.get("window_href")
            if "/website_payment" in href:
                url_params = request.params.get("window_href").split("?")[1].split("&")
                params_dict = {}
                for params in url_params:
                    params_dict[params.split("=")[0]] = params.split("=")[1]
                sale_sequence = (
                    self.env["ir.sequence"].sudo().search([("code", "=", "sale.order"), ("active", "=", True)])
                )
                if sale_sequence.prefix and params_dict.get("reference"):
                    if sale_sequence.prefix in params_dict.get("reference"):
                        exist_order = (
                            self.env["sale.order"].sudo().search([("name", "=", params_dict.get("reference"))])
                        )
            if "/shop/payment" in href and data.get("order_id"):
                order_id = data.get("order_id")
                exist_order = self.env["sale.order"].sudo().search([("id", "=", order_id)])

            if "/my/orders" in href:
                order_id = href.split("/my/orders/")[1].split("?")[0].split("/")[0]
                exist_order = self.env["sale.order"].sudo().search([("id", "=", order_id)])

            if "/my/payment_method" not in href:
                if exist_order and exist_order.batch_id and exist_order.bambora_batch_payment_id:
                    if exist_order.bambora_batch_state:
                        msg = "You cannot create a separate Transaction for this Order. You already have Batch Payment-%s alocated to this Order" \
                                % (exist_order.bambora_batch_payment_id)
                        raise UserError(_(msg))



    def bamboraeft_s2s_form_validate(self, data):
        if data.get("order_id"):
            order = self.env["sale.order"].sudo().search([("id", "=", data.get("order_id"))])
            if order:
                data["order_name"] = order.name
                data["charge_total"] = order.amount_total
        error = {}

        if data.get("bamboraTran") == "on":
            _logger.info("\nPayment by Card")
            mandatory_fields = [
                "providerid",
                "providerstate",
                "bamboraeft_merchant_id",
                "bamboraeft_batch_api",
                "bamboraeft_report_api",
                "cc_number",
                "cc_holder_name",
                "cc_expiry",
                "cvc",
            ]
        else:
            mandatory_fields = [
                "providerid",
                "providerstate",
                "bamboraeft_merchant_id",
                "bamboraeft_batch_api",
                "bamboraeft_report_api",
                "acc_holder_name",
                "acc_number",
                "bank_account_type",
                "institution_number",
                "branch_number",
                "bank_name",
            ]

        if "/payment_method" not in request.params.get("window_href"):
            mandatory_fields += ["order_name", "charge_total"]

        data = self.get_website_payment(data)

        if "/my/orders/" in request.params.get("window_href"):
            window_href = request.params.get("window_href")
            model = "sale.order"
            order_id = window_href.rsplit("/my/orders/")[1].split("?")[0]
            if order_id:
                order_rec = self.env[model].sudo().search([("id", "=", order_id)])
                data["order_name"] = order_rec.name
                data["charge_total"] = order_rec.amount_total
                if order_rec.batch_id or order_rec.bambora_batch_payment_id:
                    msg = "You already have a payment for this Sale Order. You cannot create another Bambora EFT Payment for this Sale Order."
                    raise UserError(_(msg))

        if "/my/invoices/" in request.params.get("window_href"):
            window_href = request.params.get("window_href")
            model = "account.move"
            invoice_id = window_href.rsplit("/my/invoices/")[1].split("?")[0]
            if invoice_id:
                invoice_rec = self.env[model].sudo().search([("id", "=", invoice_id)])
                data["order_name"] = invoice_rec.name
                data["charge_total"] = invoice_rec.amount_total

        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = "missing"
        _logger.warning("ERROR" + str(error))
        return False if error else True


    def get_website_payment(self, data):
        if "website_payment" in request.params.get("window_href"):
            href = request.params.get("window_href") or request.httprequest.url
            url_string = urllib.parse.unquote(href)
            url_string = url_string.split("?")[1].split("&")
            url_params = {}
            for param in url_string:
                url_params[param.split("=")[0]] = param.split("=")[1]
            if url_params.get("reference") and url_params.get("order_id"):
                model = "sale.order"
                domain = [("id", "=", url_params.get("order_id"))]
                domain += [("name", "=", url_params.get("reference"))]
                order_rec = self.env[model].sudo().search(domain)
                if order_rec:
                    # order_id = order_rec.id
                    data["order_name"] = order_rec.name
                    data["charge_total"] = order_rec.amount_total
                else:
                    model = "account.move"
                    invoice_rec = self.env[model].sudo().search(domain, limit=1)
                    # invoice_id = invoice_rec.id
                    data["order_name"] = invoice_rec.name
                    data["charge_total"] = invoice_rec.amount_total

        return data

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
    # bamboraeft_batch_id = fields.Char(string='Batch Id')
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


    def get_payment_token(self, order_number):
        if self.payment_token_id.bambora_token_type == "permanent":
            _logger.info("\n--->permanent")
            req = {
                "payment_method": "payment_profile",
                "order_number": order_number,
                "amount": self.sale_order_ids[0].amount_total,
                "payment_profile": {
                    "customer_code": self.payment_token_id.bambora_profile,
                    "card_id": "1",
                    "complete": "true",
                },
            }
        else:
            _logger.info("\n--->Temporary")
            req = {
                "payment_method": "token",
                "order_number": order_number,
                "amount": self.sale_order_ids[0].amount_total,
                "token": {
                    "code": self.payment_token_id.bambora_token,
                    "name": self.sale_order_ids[0].partner_id.name,
                    "complete": "true",
                },
            }

        return req

    def deactivate_profile(self):
        false_profiles = (
            self.env["payment.token"]
            .sudo()
            .search(
                [
                    ("providerid.provider", "=", "bamboraeft"),
                    ("active", "=", True),
                    ("bambora_token_type", "!=", "permanent"),
                ]
            )
        )
        for profile in false_profiles:
            profile.sudo().write({"active": False})

    def bamboraeft_s2s_do_transaction(self, **data):
        _logger.info("bamboraeft_s2s_do_transaction ===>>> %s" % str(data))
        self.ensure_one()
        self.deactivate_profile()
        window_href = request.params.get("window_href") or request.httprequest.url
        if "call_button" in window_href:
            # model = "account.move"
            params = dict(request.params)
            if params.get("method") == "action_create_payments" and params.get("model") == "account.payment.register":
                pay_reg = (
                    self.env["account.payment.register"].sudo().search([("id", "in", params["args"][0])], limit=1)
                )
                if pay_reg and pay_reg.communication:
                    move_id = self.env["account.move"].sudo().search([("name", "=", pay_reg.communication)], limit=1)
                    if move_id.batch_id:
                        raise UserError(_('You already have a batch payment for Invoice-%s') % move_id.name)
            _logger.info("self.partner_country_id ===>>> %s" %str(self.partner_country_id))
            _logger.info("self.partner_id.country_id ===>>> %s" %str(self.partner_id.country_id))

        if not self.partner_country_id and self.partner_id.country_id:
            self.partner_country_id = self.partner_id.country_id.id

        if not self.partner_id.country_id or not self.partner_country_id:
            raise UserError(
                _("Please add country for this customer. Country Field cannot be empty for Bambora EFT Payment!")
            )

        acq = request.env["payment.provider"].search([("id", "=", int(self.payment_token_id.providerid))])
        if acq and self.payment_token_id.bamboraeft_tran_type == "bank":
            res_json = self.action_register_bambora_batch_payment(data)

        if acq and self.payment_token_id.bamboraeft_tran_type == "card":
            order_number = self.sale_order_ids[0].name + "/" + str(get_random_string(6))
            url = "https://api.na.bambora.com/v1/payments"

            req = self.get_payment_token(order_number)
            _logger.info(req)

            headers = get_headers(
                self.providerid.bamboraeft_merchant_id,
                self.providerid.bamboraeft_payment_api,
            )
            response = requests.post(url, data=json.dumps(req), headers=headers)
            _logger.info(response.status_code)
            _logger.info(response.text)
            if response.status_code == 200:
                res_json = response.json()
            else:
                _logger.warning(
                    "Error Code:"
                    + str(response.status_code)
                    + "\n"
                    + "Payment Response from Bambora:"
                    + str(response.json().get("message"))
                )
                raise ValidationError(
                    "Error Code:"
                    + str(response.status_code)
                    + "\n"
                    + "Payment Response from Bambora:"
                    + str(response.json().get("message"))
                )

        res_json = self.return_form_data(res_json)
        return self._bamboraeft_s2s_validate_tree(res_json)

    def return_order_rec(self):
        model = False
        order_id = False
        order_rec = False
        if "/shop/payment" in request.httprequest.url:
            model = "sale.order"
            order_id = request.params.get("order_id") or request.session.get("sale_order_id") or False
            if order_id:
                order_rec = self.env[model].sudo().search([("id", "=", order_id)])

        if "/my/orders" in request.httprequest.url:
            model = "sale.order"
            order_id = request.httprequest.url.rsplit("/")[1].split("?")[0]
            if order_id:
                order_rec = self.env[model].sudo().search([("id", "=", order_id)])

        return model, order_id, order_rec

    def return_form_data(self, res_json):
        form_data = {}
        invoice_id = False
        order_id = False
        order_rec = False
        invoice_rec = False

        model, order_id, order_rec = self.return_order_rec()

        if "/my/invoices" in request.httprequest.url:
            model = "account.move"
            invoice_id = request.httprequest.url.rsplit("/")[1].split("?")[0]
            if invoice_id:
                invoice_rec = self.env[model].sudo().search([("id", "=", invoice_id)])

        if "/invoice/pay/" in request.httprequest.url:
            model = "account.move"
            invoice_id = request.httprequest.url.rsplit("/invoice/pay/")[1].split("/")[0]
            if invoice_id:
                invoice_rec = self.env[model].sudo().search([("id", "=", invoice_id)])

        if "website_payment" in request.httprequest.url:
            window_href = request.params.get("window_href")
            url_string = window_href.split("?")[1].split("&") or request.httprequest.url.split("?")[1].split("&")
            url_params = {}
            for param in url_string:
                url_params[param.split("=")[0]] = param.split("=")[1]
            if url_params.get("reference") and url_params.get("order_id"):
                model = "sale.order"
                domain = [("id", "=", url_params.get("order_id"))]
                domain += [("name", "=", url_params.get("reference"))]
                order_rec = self.env[model].sudo().search(domain)
                if order_rec:
                    order_id = order_rec.id
                else:
                    model = "account.move"
                    invoice_rec = self.env[model].sudo().search(domain, limit=1)
                    invoice_id = invoice_rec.id

        window_href = request.params.get("window_href") or request.httprequest.url
        if "call_button" in window_href:
            invoice_rec, invoice_id = self.return_invoice_rec()

        form_data["model"] = model
        form_data["invoice_id"] = invoice_id
        form_data["order_id"] = order_id
        res_json["form_data"] = form_data
        res_json["order_rec"] = order_rec
        res_json["invoice_rec"] = invoice_rec
        return res_json

    def return_invoice_rec(self):
        model = "account.move"
        invoice_rec = self.invoice_ids[0] if len(self.invoice_ids) > 0 else False
        invoice_id = self.invoice_ids[0].id if len(self.invoice_ids) > 0 else False
        if not invoice_id:
            params = dict(request.params)
            invoice_rec_ids = []
            if (
                params.get("method") == "action_create_payments"
                and params.get("model") == "account.payment.register"
            ):
                pay_reg = (
                    self.env["account.payment.register"].sudo().search([("id", "in", params["args"][0])], limit=1)
                )
                if pay_reg and pay_reg.communication:
                    invoice_rec = (
                        self.env["account.move"].sudo().search([("name", "=", pay_reg.communication)], limit=1)
                    )
                    if not invoice_rec:
                        for line_id in pay_reg.line_ids:
                            invoice_rec_ids += (
                                line_id.move_id.ids if line_id.move_id.id not in invoice_rec_ids else []
                            )
                            invoice_rec = (
                                self.env["account.move"].sudo().search([("id", "in", invoice_rec_ids)], limit=1)
                                if len(invoice_rec_ids) == 1
                                else invoice_rec
                            )
                else:
                    for line_id in pay_reg.line_ids:
                        invoice_rec_ids += line_id.move_id.ids if line_id.move_id.id not in invoice_rec_ids else []
                        invoice_rec = (
                            self.env["account.move"].sudo().search([("id", "in", invoice_rec_ids)], limit=1)
                            if len(invoice_rec_ids) == 1
                            else invoice_rec
                        )
            invoice_id = invoice_rec.id

        return invoice_rec, invoice_id

    def _bamboraeft_s2s_validate_tree(self, tree):
        return self._bamboraeft_s2s_validate(tree)

    def get_partner_id(self):
        partner_country_id = False
        partner_country_id = (
            self.sale_order_ids[0].partner_id.country_id.id if len(self.sale_order_ids) > 0 else partner_country_id
        )
        partner_country_id = (
            self.invoice_ids[0].partner_id.country_id.id if len(self.invoice_ids) > 0 else partner_country_id
        )
        return partner_country_id


    def _bamboraeft_s2s_validate(self, tree):
        tx = self
        acc_move = self.env["account.move"].sudo()
        invoice_rec_ids = []
        partner_country_id = self.get_partner_id()

        if tree.get("code") == 1 and tree.get("batch_id"):
            # if self.providerid.debug_logging:
            #     _logger.info("_bamboraeft_s2s_validate===>>>>>>>>")
            #     _logger.info(pprint.pformat(tree))
            #     _logger.info("partner_country_id===>>>>>>>>" + str(partner_country_id))
            #     _logger.info("""Batch Payment************""")
            #     _logger.info(str(tree.get("message")))

            transaction = {}
            transaction["partner_country_id"] = self.partner_country_id or partner_country_id
            transaction["state"] = "pending"
            transaction["state_message"] = tree.get("message")
            transaction["type"] = "validation"
            _logger.info("Validated bamboraeft s2s payment for tx %s: set as pending" % (tx.reference))
            # tx.write(transaction)
            ##########################################################################################
            tx._set_transaction_pending()
            ##########################################################################################
            ###OPEN LATER
            #=-==========================
            # try:
            #     tx._post_process_after_done()
            #     self.env.cr.commit()
            # except Exception:
            #     _logger.exception("Transaction post processing failed")
            #     self.env.cr.rollback()
            #=-==========================
            invoice_rec = tree.get("invoice_rec")
            if invoice_rec and not tree.get("order_rec"):
                params = dict(request.params)

                if (
                    params.get("method") == "action_create_payments"
                    and params.get("model") == "account.payment.register"
                ):
                    pay_reg = (
                        self.env["account.payment.register"]
                        .sudo()
                        .search([("id", "in", params["args"][0])], limit=1)
                    )
                    if pay_reg and pay_reg.communication:
                        invoice_rec = acc_move.search([("name", "=", pay_reg.communication)], limit=1)
                        if not invoice_rec:
                            for line_id in pay_reg.line_ids:
                                invoice_rec_ids += (
                                    line_id.move_id.ids if line_id.move_id.id not in invoice_rec_ids else []
                                )
                                invoice_rec = (
                                    self.env["account.move"]
                                    .sudo()
                                    .search([("id", "in", invoice_rec_ids)], limit=1)
                                    if len(invoice_rec_ids) == 1
                                    else invoice_rec
                                )
                    else:
                        for line_id in pay_reg.line_ids:
                            invoice_rec_ids += (
                                line_id.move_id.ids if line_id.move_id.id not in invoice_rec_ids else []
                            )
                        invoice_rec = (
                            self.env["account.move"].sudo().search([("id", "in", invoice_rec_ids)], limit=1)
                            if len(invoice_rec_ids) == 1
                            else invoice_rec
                        )

                if invoice_rec.state == "posted" and self.state == "pending":
                    invoice_rec.sudo().write(
                        {
                            "payment_state": "in_payment",
                            "bambora_batch_state": "scheduled",
                            # "payment_id":self.payment_id,
                        }
                    )

                if self.providerid.debug_logging:
                    _logger.info("invoice_rec_ids===>>>>>>>>%s" %str(invoice_rec_ids))
                    _logger.info("invoice_rec===>>>>>>>>%s" %str(invoice_rec))

                return False
            return True

    def create_datalist(self, data, eft_type, check_prefix, invoice_id, records, dynamic_descriptor):
        data_list = []
        if self.payment_token_id.providerid.bamboraeft_create_profile:
            _logger.info("Pay with Bambora Profile")
            data_list = [
                [
                    record.providerid.bamboraeft_transaction_type,
                    eft_type,
                    "",
                    "",
                    "",
                    round(record.amount * 100),
                    record.reference if check_prefix not in str(invoice_id.name) else str(invoice_id.name),
                    record.partner_id.name,
                    record.payment_token_id.bambora_profile,
                    dynamic_descriptor,
                ]
                for record in records
            ]
        else:
            _logger.info("Pay with Account Number Only")
            if self.payment_token_id.providerid.bamboraeft_transaction_type == "E":
                data_list = [
                    [
                        "E",
                        eft_type,
                        data["institution_number"],
                        data["branch_number"],
                        data["acc_number"],
                        round(record.amount * 100),
                        record.reference if check_prefix not in str(invoice_id.name) else str(invoice_id.name),
                        record.partner_id.name,
                    ]
                    for record in records
                ]
            else:
                data_list = [
                    [
                        "A",
                        eft_type,
                        data["institution_number"],
                        data["branch_number"],
                        data["acc_number"],
                        round(record.amount * 100),
                        record.reference if check_prefix not in str(invoice_id.name) else str(invoice_id.name),
                        record.partner_id.name,
                    ]
                    for record in records
                ]

        return data_list

    def action_get_orders(self, window_href, data):
        payment_type = "Customer"
        eft_type = "D"
        order_rec = False
        records = False
        if "call_button" not in window_href:
            if "/my/orders" in request.params.get("window_href"):
                order_id = data.get("order_id") or window_href.split("/my/orders/")[1].split("?")[0].split("/")[0]
                records = self.env["sale.order"].sudo().search([("id", "=", order_id)])
                payment_type = "Customer"
                eft_type = "D"
                order_rec = records[0]

            if "/website_payment" in request.params.get("window_href"):
                url_params = request.params.get("window_href").split("?")[1].split("&")
                params_dict = {}
                for params in url_params:
                    params_dict[params.split("=")[0]] = params.split("=")[1]

                sale_sequence = self.env["ir.sequence"].sudo().search([("code", "=", "sale.order"), ("active", "=", True)])
                if sale_sequence.prefix and params_dict.get("reference"):
                    if sale_sequence.prefix in params_dict.get("reference"):
                        records = self.env["sale.order"].sudo().search([("name", "=", params_dict.get("reference"))])
                        order_rec = records[0]
                if "INV" in params_dict.get("reference") or "RINV" in params_dict.get("reference"):
                    records = self.env["account.move"].sudo().search([("name", "=", params_dict.get("reference"))])

            if "/shop/payment" in request.params.get("window_href"):
                records = self.sale_order_ids if len(self.sale_order_ids) > 0 else None
                order_rec = records[0]

        return payment_type,eft_type,order_rec,records

    def action_register_bambora_batch_payment(self, data):
        pass_code = "Passcode " + get_authorization(
            self.providerid.bamboraeft_merchant_id, self.providerid.bamboraeft_batch_api
        )
        window_href = request.params.get("window_href") or request.httprequest.url
        if "call_button" in window_href:
            _logger.info("""call_button""")
            if self.invoice_ids:
                records = self.invoice_ids

        payment_type,eft_type,order_rec,records = self.action_get_orders(window_href, data)
        #------------------------------------------------------------------------------------------------------------
        # else:
        #     if "/my/orders" in request.params.get("window_href"):
        #         order_id = data.get("order_id") or window_href.split("/my/orders/")[1].split("?")[0].split("/")[0]
        #         records = self.env["sale.order"].sudo().search([("id", "=", order_id)])
        #         payment_type = "Customer"
        #         eft_type = "D"
        #         order_rec = records[0]

        #     if "/website_payment" in request.params.get("window_href"):
        #         url_params = request.params.get("window_href").split("?")[1].split("&")
        #         params_dict = {}
        #         for params in url_params:
        #             params_dict[params.split("=")[0]] = params.split("=")[1]

        #         sale_sequence = self.env["ir.sequence"].sudo().search([("code", "=", "sale.order"), ("active", "=", True)])
        #         if sale_sequence.prefix and params_dict.get("reference"):
        #             if sale_sequence.prefix in params_dict.get("reference"):
        #                 records = self.env["sale.order"].sudo().search([("name", "=", params_dict.get("reference"))])
        #                 order_rec = records[0]
        #         if "INV" in params_dict.get("reference") or "RINV" in params_dict.get("reference"):
        #             records = self.env["account.move"].sudo().search([("name", "=", params_dict.get("reference"))])

        #     if "/shop/payment" in request.params.get("window_href"):
        #         records = self.sale_order_ids if len(self.sale_order_ids) > 0 else None
        #         order_rec = records[0]
        #------------------------------------------------------------------------------------------------------------
        # data_list format
        # 1. Transaction type (E/A)
        # 2. Transaction type (C/D)
        # 3. Financial institution number - The 3 digit financial institution number
        # 4. Bank transit number - The 5 digit bank transit number
        # 5. Account number - The 5-12 digit account number
        # 6. Amount - Transaction amount in pennies
        # 7. Reference number - An optional reference number of up to 19 digits. If you don't want a reference number, enter "0" (zero).
        # 8. Recipient name - Full name of the bank account holder
        # 9. Customer code - The 32-character customer code located in the Payment Profile. Do not populate bank account fields in the file when processing against a Payment Profile.
        # 10. Dynamic descriptor - By default the Bambora merchant company name will show on your customer's bank statement. You can override this default by populating the Dynamic Descriptor field.

        records = self
        eft_type = "D"
        dynamic_descriptor = self.payment_token_id.providerid.bamboraeft_dynamic_desc or ""
        payment_type = "Customer"
        #----------------------------------------------------------------------------------------------------------------
        # if self.invoice_ids.move_type == "out_invoice":
        # payment_type = "Customer" if self.invoice_ids.move_type == "out_invoice" else "Vendor"
        # eft_type = "D" if self.invoice_ids.move_type == "out_invoice" else "C"
        # if self.invoice_ids.move_type == "in_invoice":
        #----------------------------------------------------------------------------------------------------------------
        payment_type = "Vendor" if self.invoice_ids.move_type == "in_invoice" else payment_type
        eft_type = "C"  if self.invoice_ids.move_type == "in_invoice" else eft_type

        invoice_id = self.invoice_ids[0] if len(self.invoice_ids) > 0 else self.env["account.move"]
        check_prefix = "RINV"
        params = dict(request.params) or {}
        if params and self.payment_id:
            if params.get("method") == "action_create_payments" and params.get("model") == "account.payment.register":
                eft_type = "C" if self.payment_id.payment_type == "outbound" else "D"
                context = dict(self.env.context)
                invoice_id = (
                    self.env["account.move"].browse(context["active_id"])
                    if context.get("active_id")
                    else self.env["account.move"]
                )
                _logger.info("invoice_idName-===>>>%s" % str(invoice_id.name))
                payment_type = INVOICE_MOVE_TYPES.get(invoice_id.move_type) if invoice_id and invoice_id.move_type else payment_type

        data_list = self.create_datalist(data, eft_type, check_prefix, invoice_id, records, dynamic_descriptor)
        # if "/shop/payment" in window_href:
        payment_type = "Customer" if "/shop/payment" in window_href else payment_type
        eft_type = "D" if "/shop/payment" in window_href else eft_type
        # if self.providerid.debug_logging:
        #     _logger.info(_("Pay with Bank"))
        #     _logger.info(_("records===>>>%s" % str(records)) )
        #     msg = str(payment_type) + " Payment===>>>>" + str(self.invoice_ids.move_type) + ":" + str(self.amount)
        #     _logger.info(_(msg))
        #     _logger.info(_("eft_type===>>>%s" % str(eft_type)))
        #     _logger.info(_("data_list===>>>>" + str(data_list)))
        folder_path = os.getenv("HOME") + "/bamboraFiles"
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)

        csv_name = str(datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".csv"
        filename = os.path.expanduser(os.getenv("HOME")) + "/bamboraFiles/" + csv_name
        with open(filename, "w", encoding="UTF8", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data_list)

        dict_data = {
            "process_now": 1,
            # "process_date": datetime.date.today().strftime("%Y%m%d")
        }

        json_data = json.dumps(dict_data)

        files = (
            ("criteria", (None, json_data, "application/json")),
            ("file", open(filename, "rb")),
        )

        headers = {
            "authorization": pass_code,
        }
        response = requests.post(BATCH_API, headers=headers, files=files)
        response_dict = json.loads(response.text)
        model,invoice_id,invoice_rec = self.action_get_invoice()
        self.action_process_response(response, response_dict, records, invoice_rec, order_rec)
        try:
            os.remove(filename)
        except Exception:
            _logger.info("Error for Deleting Files")
        return response_dict

    def action_process_response(self, response, response_dict, records, invoice_rec, order_rec):
        vals = {}
        track_id = False
        if response and response.status_code == 200:
            try:
                for rec in records:
                    vals = {
                        "transaction_date": datetime.date.today(),
                        "invoice_no": invoice_rec.id,
                        "invoice_ref": rec.reference,
                        "invoice_partner_id": rec.partner_id.id,
                        "partner_bank_id": rec.payment_token_id.partner_bank_id,
                        "invoice_date": rec.date,
                        "batch_id": response_dict.get("batch_id"),
                        "state": "scheduled",
                        "sale_ok": True if rec.sale_order_ids is not False else False,
                        "transaction_ids": rec.ids,
                        "providerid": rec.providerid.id,
                    }
                    track_id = self.env["batch.payment.tracking"].sudo().create(vals) if len(vals) > 0 else False
                    rec.write(
                        {
                            "bamboraeft_batch_id": track_id.id,
                            "bamboraeft_batch_mode": response_dict.get("batch_mode"),
                            "bamboraeft_code": response_dict.get("code"),
                            "bamboraeft_message": response_dict.get("message"),
                            "bamboraeft_process_date": response_dict.get("process_date"),
                            "bamboraeft_process_time_zone": response_dict.get("process_time_zone"),
                        }
                    )

                    if invoice_rec:
                        invoice_rec.write({"bambora_batch_payment_id": track_id.id})
                    try:
                        if order_rec:
                            order_vals =  {
                                    "batch_id": response_dict.get("batch_id"),
                                    "bambora_batch_payment_id": track_id.id,
                            }
                            order_rec.write(order_vals)
                            order_rec.action_confirm()
                    except Exception as e:
                        _logger.info("Order Rec Errors====>>>%s" %str(e.args))

            except Exception as e:
                _logger.info("Errors====>>>%s" %str(e.args))


        if self.providerid.debug_logging:
            _logger.info("response_dict===>>>>>")
            _logger.info(pprint.pformat(response_dict))
            _logger.info("Vals ===>>> %s" % (str(vals)))
            _logger.info("Batch Track Created-%s" % (track_id))


    def action_get_invoice(self):
        invoice_id = False
        invoice_rec = self.env["account.move"]
        model = 'sale.order'
        if "/my/invoices" in request.httprequest.url:
            model = "account.move"
            invoice_id = request.httprequest.url.rsplit("/")[1].split("?")[0]
            if invoice_id:
                invoice_rec = self.env[model].sudo().search([("id", "=", invoice_id)])

        if "/invoice/pay/" in request.httprequest.url:
            model = "account.move"
            invoice_id = request.httprequest.url.rsplit("/invoice/pay/")[1].split("/")[0]
            if invoice_id:
                invoice_rec = self.env[model].sudo().search([("id", "=", invoice_id)])

        if "call_button" in request.httprequest.url:
            context = dict(self.env.context) or {}
            if context.get("active_id"):
                model = context.get("active_model")
                invoice_id = context.get("active_ids") or context.get("active_id") or False
                invoice_rec = self.env[model].sudo().search([("id", "in", invoice_id)])
                invoice_rec = invoice_rec[0] if len(invoice_rec) == 1 else invoice_rec
                if len(invoice_rec) > 1:
                    _logger.warning("Multiple Invoices Found")
        return model,invoice_id,invoice_rec

class PaymentTokenEft(models.Model):
    _inherit = "payment.token"

    bambora_profile = fields.Char()
    bambora_token = fields.Char()
    bambora_token_type = fields.Selection(
        string="Token Type",
        selection=[("temporary", "Temporary"), ("permanent", "Permanent")],
    )
    provider = fields.Selection(string="Provider", related="providerid.provider", readonly=False)
    # save_token = fields.Selection(string="Save Cards", related="providerid.save_token", readonly=False)
    bamboraeft_tran_type = fields.Selection(string="Transaction Type", selection=[("bank", "Bank"), ("card", "Card")])
    partner_bank_id = fields.Many2one(
        string="Partner Bank",
        comodel_name="res.partner.bank",
        ondelete="restrict",
    )


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()
        if len(payments) == 1:
            pay_txn = self.env["payment.transaction"].sudo().search([("payment_id", "=", payments.id)])
            if pay_txn.providerid.provider == "bamboraeft":
                payments.state = "draft"
        return payments
