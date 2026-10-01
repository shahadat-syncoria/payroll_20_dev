###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import base64
import csv
import datetime
import json
import logging
import os

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from ..utils.helper import _get_authorization

_logger = logging.getLogger(__name__)

BATCH_API = "https://api.na.bambora.com/v1/batchpayments"
REPORT_API = "https://api.na.bambora.com/scripts/reporting/report.aspx"

def bambora_payment(provider):
    icp_sudo = request.env["payment.provider"].sudo()
    bamboraeft_rec = icp_sudo.search([("code", "=", provider)])
    if not bamboraeft_rec:
        raise UserError(_("Module not install or disable!"))

    return bamboraeft_rec


class AccountInvoiceBatchPayment(models.Model):
    _inherit = "account.move"



    batch_id = fields.Char("Batch ID", readonly=True)
    bambora_batch_payment_id = fields.Many2one("batch.payment.tracking", "Bambora Batch Payment", readonly=True)
    bambora_batch_state = fields.Selection(string="Bambora State", related="bambora_batch_payment_id.state")
    bambora_batch_status = fields.Char(string="Bambora Status", related="bambora_batch_payment_id.status")
    bambora_bank_identifier_number = fields.Char(
        "Bank Identifier No.", related="partner_bank_id.bank_bic", readonly=True
    )
    bambora_bank_transit_number = fields.Char(
        "Bank Transit No.", related="partner_bank_id.bank_transit_no", readonly=True
    )

    def check_conditions(self, record):
        if record.move_type == "out_invoice":
            transaction_type = "D"  # For invoice Debit
        elif record.move_type == "in_invoice":
            transaction_type = "C"  # For Vendor Bill Credit

        pay_trx = self.env["payment.transaction"].sudo()
        tx = pay_trx.search([("reference", "=", record.name)], limit=1)
        if tx:
            raise UserError(_("%s Record already in transaction process") % record.name)
        if (
                not record.partner_bank_id.account_number
                or not record.bambora_bank_identifier_number
                or not record.bambora_bank_transit_number
                or not record.bambora_bank_identifier_number.isdigit()
                or not record.bambora_bank_transit_number.isdigit()
        ):
            raise UserError(_("Please Add Full Account Information for  %s") % record.name)
        elif record.state == "draft":
            raise UserError(_("Please only sent posted entries!! %s") % record.name)
        elif record.payment_state == "paid":
            raise UserError(_("%s invoice Already Paid!!") % record.name)
        elif not len(record.bambora_bank_identifier_number) == 3 or not len(record.bambora_bank_transit_number) == 5:
            raise UserError(_("Bank identifier must be 3 digit and transit number is 5 digit!!. For %s") % record.name)
        else:
            try:
                data = [
                    "E",
                    transaction_type,
                    record.bambora_bank_identifier_number,
                    record.bambora_bank_transit_number,
                    record.partner_bank_id.account_number,
                    round(record.amount_total * 100),
                    record.name,
                    record.partner_id.name,
                ]
                return data

            except Exception:
                raise UserError(_("Internal Error!"))

    # Bambora payment register
    def action_register_bambora_batch_payment(self):
        # icp_sudo = self.env['ir.config_parameter'].sudo()
        domain = [("code", "=", "bamboraeft")]
        providers = self.env["payment.provider"].sudo().search(domain)
        if not providers:
            raise UserError(_("Module not install or disable!"))

        try:
            pass_code = "Passcode " + _get_authorization(
                providers.bamboraeft_merchant_id, providers.bamboraeft_batch_api
            )
        except Exception:
            raise UserError(_("Check Credentials !"))
        data_list = []
        for record in self:
            data = self.check_conditions(record)
            data_list.append(data)

        folder_path = os.getenv("HOME") + "/bamboraFiles"
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)

        filename = os.path.expanduser(os.getenv("HOME")) + "/bamboraFiles/transaction.csv"
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
        try:
            response = requests.post(BATCH_API, headers=headers, files=files)
            response_dict = json.loads(response.text)
            _logger.info(str(response_dict))
        except Exception:
            raise UserError(_("Internal Error."))

        if response and response.status_code == 200:
            for rec in self:
                vals_list = {
                    "transaction_date": datetime.date.today(),
                    "invoice_no": rec.id,
                    "invoice_ref": rec.ref,
                    "invoice_partner_id": rec.partner_id.id,
                    "partner_bank_id": rec.partner_bank_id.id,
                    "invoice_date": rec.invoice_date,
                    "batch_id": response_dict["batch_id"],
                    "state": "scheduled",
                }

                batch_id = self.env["batch.payment.tracking"].create(vals_list)
                rec.write(
                    {
                        "batch_id": response_dict["batch_id"],
                        "bambora_batch_payment_id": batch_id.id,
                    }
                )
        else:
            raise UserError(_("%s" % (response_dict['message'])))

    @api.depends("commercial_partner_id")
    def _compute_bank_partner_id(self):
        for move in self:
            if move.is_outbound():
                move.bank_partner_id = move.commercial_partner_id
            else:
                move.bank_partner_id = move.commercial_partner_id
                # move.bank_partner_id = move.company_id.partner_id
