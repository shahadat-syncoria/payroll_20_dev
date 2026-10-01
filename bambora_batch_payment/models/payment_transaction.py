# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import base64
import requests
import csv
import datetime
import json
import logging
import os
import pprint
import string
import random


from odoo import _, api, models, fields
from odoo.http import request
from odoo.exceptions import UserError, ValidationError


from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

BATCH_API = "https://api.na.bambora.com/v1/batchpayments"
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

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str

class BamboraPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    bambora_auth_code = fields.Char("Auth Code")
    bambora_created = fields.Char("Bambora Created on")
    bambora_order_number = fields.Char("Order Number")
    bambora_txn_type = fields.Char("Transaction Type")
    bambora_payment_method = fields.Char("Payment Method")
    bamboraeft_tran_type = fields.Selection(string="Bambora Transaction Type",
                                            selection=[("bank", "Bank"), ("card", "Card")], related="provider_id.bamboraeft_tran_type", store=True)
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

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Bambora.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'bamboraeft':
            return
        # Make the payment request to Bambora with the saved token
        if not self.token_id:
            raise UserError("BamboraEFT: " + _("The transaction is not linked to a token."))

        data = {
            "tx_id": self.id,
        }

        response_content = self.provider_id.sudo()._bambora_make_request(
            payload=data,
            token=self.token_id
        )

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        self._record(dict(response_content, reference=self.reference))

    def get_payment_token(self, order_number, data=None, reference=None):
        so_sudo = self.env['sale.order'].sudo()
        if reference:
            order = so_sudo.search([('name', '=', reference.split('-')[0])], limit=1)
            if self.token_id.bambora_token_type == "permanent":
                _logger.info("\n--->permanent")
                req = {
                    "payment_method": "payment_profile",
                    "order_number": order_number,
                    "amount": order.amount_total,
                    "payment_profile": {
                        "customer_code": self.token_id.bambora_profile,
                        "card_id": "1",
                        "complete": "true",
                    },
                }
            else:
                _logger.info("\n--->Temporary")
                req = {
                    "payment_method": "card",
                    "order_number": order_number,
                    "amount": order.amount_total,
                    "card": {
                        "number": data["cardData"].get("cardNumber"),
                        "name": data["cardData"].get("cardNumber"),
                        "expiry_month": data["cardData"].get("month"),
                        "expiry_year": data["cardData"].get("year"),
                        "cvd": data["cardData"].get("cardCode")
                    },
                }

        return req

    def action_register_bambora_batch_payment(self, data=None, token=None):

        # Generate passcode with batch api authorization
        pass_code = "Passcode " + get_authorization(
            self.provider_id.bamboraeft_merchant_id, self.provider_id.bamboraeft_batch_api
        )

        # Prepare the datalist for preparing bamboraeft files
        data_list = self._prepare_datalist(data, token=token, payment_type="inbound")

        # Folder created for generate the temporary csv file
        folder_path = os.getenv("HOME") + "/bamboraFiles"
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)

        csv_name = str(datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".csv"
        filename = os.path.expanduser(os.getenv("HOME")) + "/bamboraFiles/" + csv_name
        with open(filename, "w", encoding="UTF8", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data_list)

        # Immediate processing the batch payment
        dict_data = {
            "process_now": 1,
        }
        json_data = json.dumps(dict_data)
        files = (
            ("criteria", (None, json_data, "application/json")),
            ("file", open(filename, "rb")),
        )
        headers = {
            "authorization": pass_code,
        }
        try:
            response = requests.post(BATCH_API, headers=headers, files=files, timeout=60)
            response.raise_for_status()
            response_dict = json.loads(response.text)

            # Saved to backend
            self._save_bamboraeft_batchpayment_response(response=response)
            response_dict.update({"reference": self.reference, "tx_id": self.id})
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", BATCH_API)
            raise ValidationError("BamboraEFT: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", BATCH_API, files, error.response.text
            )
            raise ValidationError("BamboraEFT: " + _("The communication with the API failed."))
        try:
            os.remove(filename)
        except Exception as e:
            _logger.info("Error for Deleting Files %s" % str(e.args))
        return response_dict

    def _save_bamboraeft_batchpayment_response(self, response=None):
        if response and response.status_code == 200:
            try:
                response_dict = json.loads(response.text)
                sale_order_sudo = self.env['sale.order'].sudo()
                # `transaction_ids` sets `batch_track_id` on the transactions, which requires `payment_safe_write`
                batch_payment_tracking_sudo = self.env["batch.payment.tracking"].sudo().with_context(
                    payment_safe_write=True
                )
                for tx in self:
                    order = sale_order_sudo.search([('name', '=', tx.reference.split('-')[0])], limit=1)
                    vals = {
                        "transaction_date": datetime.date.today(),
                        "invoice_ref": tx.reference,
                        "invoice_partner_id": tx.partner_id.id or False,
                        "partner_bank_id": tx.token_id and tx.token_id.partner_bank_id or False,
                        "invoice_date": tx.payment_id and tx.payment_id.date or False,
                        "batch_id": response_dict.get("batch_id"),
                        "state": "scheduled",
                        "sale_ok": True if tx.sale_order_ids is not False else False,
                        "transaction_ids": tx.ids,
                        "provider_id": tx.provider_id.id,
                    }
                    bambora_batch_payment_id = batch_payment_tracking_sudo.create(vals) if len(vals) > 0 else False
                    tx.with_context(payment_safe_write=True).write(
                        {
                            "bamboraeft_batch_id": bambora_batch_payment_id.id,
                            "bamboraeft_batch_mode": response_dict.get("batch_mode"),
                            "bamboraeft_code": response_dict.get("code"),
                            "bamboraeft_message": response_dict.get("message"),
                            "bamboraeft_process_date": response_dict.get("process_date"),
                            "bamboraeft_process_time_zone": response_dict.get("process_time_zone"),
                        }
                    )
                    try:
                        if order:
                            order_vals = {
                                    "batch_id": response_dict.get("batch_id"),
                                    "bambora_batch_payment_id": bambora_batch_payment_id.id,
                            }
                            order.write(order_vals)
                            order.action_confirm()
                    except Exception as e:
                        _logger.error("Errors: %s" % str(e.args))

            except Exception as e:
                _logger.error("Errors: %s" % str(e.args))

        if self.provider_id.debug_logging:
            _logger.info("Process batch payment response-%s" % pprint.pformat(response_dict))
            _logger.info("Batch Track Created-%s" % pprint.pformat(response_dict))

    def bamboraeft_card_payment_transaction(self, data=None, token=None):
        _logger.info("BamboraEFT: Card payment started")
        order_number = self.reference + "/" + str(get_random_string(6))
        url = "https://api.na.bambora.com/v1/payments"

        req = self.get_payment_token(order_number, data=data, reference=self.reference)

        headers = get_headers(
            self.provider_id.bamboraeft_merchant_id,
            self.provider_id.bamboraeft_payment_api,
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

        return res_json
    def _prepare_datalist(self, data, token=None, payment_type=None):
        """
        ------------------------------------------------------------------------------------------------------------
        data_list format
        1. Transaction type (E/A)
        2. Transaction type (C/D)
        3. Financial institution number - The 3 digit financial institution number
        4. Bank transit number - The 5 digit bank transit number
        5. Account number - The 5-12 digit account number
        6. Amount - Transaction amount in pennies
        7. Reference number - An optional reference number of up to 19 digits. If you don't want a reference number, enter "0" (zero).
        8. Recipient name - Full name of the bank account holder
        9. Customer code - The 32-character customer code located in the Payment Profile. Do not populate bank account fields in the file when processing against a Payment Profile.
        10. Dynamic descriptor - By default the Bambora merchant company name will show on your customer's bank statement. You can override this default by populating the Dynamic Descriptor field.
        """
        data_list = []
        if payment_type == 'inbound':
            eft_type = "D"
        if payment_type == 'outbound':
            eft_type = "C"

        for tx in self:
            if eft_type != '':
                dynamic_descriptor = str(tx.reference)
                if token and token.bambora_profile:
                    _logger.info("Pay with Bambora Profile")
                    data_list = [
                        [
                            tx.provider_id.bamboraeft_transaction_type,
                            eft_type,
                            "",
                            "",
                            "",
                            round(tx.amount * 100),
                            tx.reference,
                            tx.partner_id.name,
                            token.bambora_profile,
                            dynamic_descriptor,
                        ]
                    ]
                else:
                    _logger.info("Pay with Account Number Only")
                    if tx.provider_id.bamboraeft_transaction_type == "E":
                        data_list = [
                            [
                                "E",
                                eft_type,
                                data['bankData']["institutionNumber"],
                                data['bankData']["branchNumber"],
                                data['bankData']["accountNumber"],
                                round(tx.amount * 100),
                                tx.reference,
                                tx.partner_id.name,
                            ]
                        ]
                    else:
                        data_list = [
                            [
                                "A",
                                eft_type,
                                data['bankData']["institutionNumber"],
                                data['bankData']["branchNumber"],
                                data['bankData']["accountNumber"],
                                round(tx.amount * 100),
                                tx.reference,
                                tx.partner_id.name,
                            ]
                        ]
        return data_list

    def _extract_amount_data(self, payment_data):
        """ Override of payment to skip the amount validation (the batch response has no amount). """
        if self.provider_code != 'bamboraeft':
            return super()._extract_amount_data(payment_data)
        return None

    def _apply_updates(self, payment_data):
        """ Override of payment to update the transaction based on BamboraEFT data.

        Note: self.ensure_one() from `_process`

        :param dict payment_data: The payment data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._apply_updates(payment_data)
        if self.provider_code != 'bamboraeft':
            return
        data = payment_data

        # Handle the provider reference
        if 'batch_id' in data:
            self.provider_reference = data.get('batch_id')

        # Handle the payment state
        payment_state = data.get('code')
        if not payment_state:
            raise ValidationError("BamboraEFT: " + _("Received data with missing payment state."))

        if payment_state == 1:
            if self.tokenize:
                self._bamboraeft_tokenize_from_feedback_data(data)
            self._set_pending()
        # elif payment_state == 2:
        #     has_token_data = 'recurring.recurringDetailReference' in data.get('additionalData', {})
        #     if self.tokenize and has_token_data:
        #         self._adyen_tokenize_from_feedback_data(data)
        #     self._set_done()
        #     if self.operation == 'refund':
        #         self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        # elif payment_state in RESULT_CODES_MAPPING['cancel']:
        #     _logger.warning("The transaction with reference %s was cancelled (reason: %s)",
        #                     self.reference, refusal_reason)
        #     self._set_canceled()
        # elif payment_state in RESULT_CODES_MAPPING['error']:
        #     _logger.warning("An error occurred on transaction with reference %s (reason: %s)",
        #                     self.reference, refusal_reason)
        #     self._set_error(
        #         _("An error occurred during the processing of your payment. Please try again.")
        #     )
        # elif payment_state in RESULT_CODES_MAPPING['refused']:
        #     _logger.warning("The transaction with reference %s was refused (reason: %s)",
        #                     self.reference, refusal_reason)
        #     self._set_error(_("Your payment was refused. Please try again."))
        # else:  # Classify unsupported payment state as `error` tx state
        #     _logger.warning("received data with invalid payment state: %s", payment_state)
        #     self._set_error(
        #         "BamboraEFT: " + _("Received data with invalid payment state: %s", payment_state)
        #     )


    def _bamboraeft_tokenize_from_feedback_data(self, data):
        # Payment check the bank details
        if self.partner_id:
            bank_name = self.check_bank_acc(data, partner=self.partner_id)
            tran_type = str(self.bamboraeft_tran_type)

            values = {}
            if tran_type == 'card':
                _logger.info("Payment by Card")
            if tran_type == 'bank':
                _logger.info("Payment by Bank Number")
            partner = self.partner_id and str(self.partner_id.name) + "[ " + str(self.partner_id.id) +" ]"
            comments = "Create Token for Customer-%s, %s" % (
                partner,
                tran_type,
            )
            values = {
                "bambora_token_type": "temporary",
                "provider_id": self.provider_id.id or False,
                "payment_method_id": self.payment_method_id.id or self.env.ref(
                    "bambora_batch_payment.payment_method_bambora_eft").id,
                "partner_id": self.partner_id.id or False,
                "provider_ref": "BamboraEFT - Batch id: " + str(data.get("batch_id")) + "Processed on " + str(data.get("process_date")),
            }
            token_name = ''
            if data['data']['bankData']:
                token_name = data['data']['bankData'].get("accountNumber")
                token_name = (
                    "***" + token_name[-4:] + " (EFT)"
                )
            values["bamboraeft_tran_type"] = self.bamboraeft_tran_type
            values["payment_details"] = token_name  # Odoo 20: payment.token has no `name` field

            if self.provider_id.bamboraeft_create_profile:

                # Create a New Profile for Bank Account or Credit Card to bambora
                profile_response = self._bamboraeft_create_profile(data=data, comments=comments)
                self._process_bank_account_response(values, data, bank_name, response=profile_response)

            # Create Token in odoo backend
            token = self.env["payment.token"].sudo().create(values)
            self.token_id = token.id
            _logger.info(values)
            _logger.info(token)
        return token

    def _bamboraeft_create_profile(self, data=None, comments=None):
        response_dict = {}
        if data and comments:
            pro_data = {
                "language": "en",
                "comments": comments,
                "bank_account": {
                    "bank_account_holder": data['data']['bankData'].get("nameOnAccount"),
                    "account_number": data['data']['bankData'].get("accountNumber"),
                    "bank_account_type": data['data']['bankData'].get("accountType"),
                    "institution_number": data['data']['bankData'].get("institutionNumber"),
                    "branch_number": data['data']['bankData'].get("branchNumber"),
                },
            }
            _logger.info(pprint.pformat(data))
            headers = get_headers(self.provider_id.bamboraeft_merchant_id, self.provider_id.bamboraeft_profile_api)

            try:
                response = requests.post(PROFILE_URL, data=json.dumps(pro_data), headers=headers)
                response.raise_for_status()
                response_dict = response
            except requests.exceptions.ConnectionError:
                _logger.exception("unable to reach endpoint at %s", PROFILE_URL)
                raise ValidationError("BamboraEFT: " + _("Could not establish the connection to the API."))
            except requests.exceptions.HTTPError as error:
                _logger.exception(
                    "invalid API request at %s with data %s: %s", PROFILE_URL, pro_data, error.response.text
                )
                raise ValidationError("BamboraEFT: " + _("The communication with the API failed."))

        return response_dict

    def check_bank_acc(self, data, partner=None):
        bank_name = False
        res_partner_bank_sudo = self.env["res.partner.bank"].sudo()
        res_partner_sudo = self.env["res.partner"].sudo()
        if self.partner_id:
            bank_account_id = res_partner_bank_sudo.search([("account_number", "=", data['data']['bankData'].get("accountNumber"))])
            if bank_account_id:
                msg = 'You cannot use this Account Number as it is already used. Please use a different account number!'
                raise UserError(_(msg))

        if partner and data['data']['bankData'].get("bankName"):
            # res.bank no longer exists in Odoo 20: the bank name and BIC live on res.partner.bank.
            bank_name = data['data']['bankData'].get("bankName")

        return bank_name

    def _create_bank_account(self, bank_name, data):
        try:

            res_partner_bank_sudo = self.env["res.partner.bank"].sudo()
            if self.partner_id and bank_name:
                partner_bank_id = self.partner_id.bank_ids.filtered(lambda c: c.account_number == data['data']['bankData'].get("accountNumber"))
                bank_account_vals = {}
                bank_account_vals["holder_name"] = data['data']['bankData'].get("nameOnAccount")
                bank_account_vals["account_number"] = data['data']['bankData'].get("accountNumber")
                bank_account_vals["bank_bic"] = data['data']['bankData'].get("institutionNumber")
                bank_account_vals["bank_transit_no"] = data['data']['bankData'].get("branchNumber")
                bank_account_vals["partner_id"] = self.partner_id and self.partner_id.id or False
                bank_account_vals["bank_name"] = bank_name
                partner_bank_id = (
                    res_partner_bank_sudo.create(bank_account_vals)
                    if not partner_bank_id
                    else partner_bank_id.write(bank_account_vals)
                )
            else:
                _logger.warning("Bank Name not provided")
        except Exception as e:
            _logger.warning("Exceptions" + str(e.args))

    def _process_bank_account_response(self, values, data, bank_name, response=None):
        res_partner_bank_sudo = self.env["res.partner.bank"].sudo()
        if response and response.status_code == 200:
            response_dict = response.json()
            if response_dict.get("code") == 1:
                _logger.info("Bambora Profile successfully created")
                values["bambora_profile"] = response_dict.get("customer_code")
                values["bambora_token_type"] = "permanent"
                try:
                    # Create a Bank Account for the Customer in bambora
                    if self.partner_id and bank_name:
                        partner_bank_id = self.partner_id.bank_ids.filtered(lambda c: c.account_number == data['data']['bankData'].get("accountNumber"))
                        bank_account_vals = {}
                        bank_account_vals["holder_name"] = data['data']['bankData'].get("nameOnAccount")
                        bank_account_vals["account_number"] = data['data']['bankData'].get("accountNumber")
                        bank_account_vals["partner_id"] = self.partner_id and self.partner_id.id or False
                        bank_account_vals["bank_name"] = bank_name
                        bank_account_vals["bank_bic"] = data['data']['bankData'].get("institutionNumber")
                        bank_account_vals["bank_transit_no"] = data['data']['bankData'].get("branchNumber")
                        bank_account_vals["bamboraeft_customer_code"] = response_dict.get("customer_code")
                        if not partner_bank_id:
                            res_partner_bank_sudo.create(bank_account_vals)
                        return values
                    else:
                        _logger.warning("Bank Name not provided")
                except Exception as e:
                    _logger.warning("Exceptions" + str(e.args))

            else:
                _logger.warning("Customer Profile: Failure")
                message = response.json().get("message")
                if message.get("details"):
                    if isinstance(message.get("details"), list):
                        for detail in message.get("details"):
                            message += "\n" + "Field Error: %s, Message: %s" % (
                                detail.get("field"),
                                detail.get("message"),
                            )

                raise ValidationError(_(message))
        else:
            message = response.json().get("message")
            if response.json().get("details"):
                if isinstance(response.json().get("details"), list):
                    for detail in response.json().get("details"):
                        message += "\n" + ",Field Error: %s, Message: %s" % (
                            detail.get("field"),
                            detail.get("message"),
                        )
            raise ValidationError(_(message))

    def _get_processing_values(self):
        res = super(BamboraPaymentTransaction,self)._get_processing_values()
        if res.get('provider_code') == 'bamboraeft':
            raise UserError(_("This Feature is not available now"))
        return res
