###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import ast
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


class HrPayslipBatchPayment(models.Model):
    _inherit = "hr.payslip"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Waiting'),
        ('done', 'Done'),
        ('waiting', 'Bambora waiting'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected')],
        string='Status', index=True, readonly=True, copy=False,
        default='draft', tracking=True,
        help="""* When the payslip is created the status is \'Draft\'
                    \n* If the payslip is under verification, the status is \'Waiting\'.
                    \n* If the payslip is confirmed then status is set to \'Done\'.
                    \n* If the payslip is process of deposit through bambora EFT then status is set to \'Bambora Waiting\'.
                    \n* When user cancel payslip the status is \'Rejected\'.""")
    batch_id = fields.Char("Batch ID", readonly=True)
    bambora_batch_payment_id = fields.Many2one("batch.payment.tracking", "Bambora Batch Payment", readonly=True)
    bambora_batch_state = fields.Selection(string="Bambora State", related="bambora_batch_payment_id.state")
    bambora_batch_status = fields.Char(string="Bambora Status", related="bambora_batch_payment_id.status")

    bambora_payroll_account_id = fields.Many2one('res.partner.bank', related='employee_id.bank_account_id')
    bambora_bank_identifier_number = fields.Char(
        "Bank Identifier No.", related="bambora_payroll_account_id.bank_bic", readonly=True
    )
    bambora_bank_transit_number = fields.Char(
        "Bank Transit No.", related="bambora_payroll_account_id.bank_transit_no", readonly=True
    )

    def action_register_bambora_batch_payment_(self):
        for pay in self:
            if pay.state == 'waiting':
                pay.write({'state': 'done'})
            else:
                pay.write({'state': 'waiting'})
    def _get_net_pay(self):
        try:
            amount = self.line_ids.filtered(lambda x: x.category_id.code == 'NET').amount
        except:
            self.message_post(body="Net pay Error")
            raise Exception(_("Net pay Error"))
        return amount
    def check_conditions(self, record):
        transaction_type = "C"

        pay_trx = self.env["payment.transaction"].sudo()
        tx = pay_trx.search([("reference", "=", record.number)], limit=1)
        if tx:
            raise UserError(_("%s Record already in transaction process") % record.name)
        if (
                not record.bambora_payroll_account_id.acc_number
                or not record.bambora_bank_identifier_number
                or not record.bambora_bank_transit_number
                or not record.bambora_bank_identifier_number.isdigit()
                or not record.bambora_bank_transit_number.isdigit()
        ):
            raise UserError(_("Please Add Full Account Information for  %s") % record.name)
        elif record.state != "done":
            raise UserError(_("Please only sent Done entries!! %s") % record.name)
        # elif record.payment_state == "paid":
        #     raise UserError(_("%s invoice Already Paid!!") % record.name)
        elif not len(record.bambora_bank_identifier_number) == 3 or not len(record.bambora_bank_transit_number) == 5:
            raise UserError(_("Bank identifier must be 3 digit and transit number is 5 digit!!. For %s") % record.name)
        else:
            try:
                data = [
                    "E",
                    transaction_type,
                    record.bambora_bank_identifier_number,
                    record.bambora_bank_transit_number,
                    record.bambora_payroll_account_id.acc_number,

                    round(record._get_net_pay() * 100),
                    record.number,
                    record.employee_id.name,
                ]
                return data

            except Exception as e:
                record.message_post(body=f"Internal Error:{e}")
                pass

    # Bambora payment register
    def action_register_bambora_batch_payment(self):
        # icp_sudo = self.env['ir.config_parameter'].sudo()
        domain = [("code", "=", "bamboraeft")]
        domain += [("state", "!=", "disabled")]
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
                    "payslip_no": rec.id,
                    "payslip_ref": rec.number,
                    "employee_id": rec.employee_id.id,
                    "partner_bank_id": rec.bambora_payroll_account_id.id,
                    "invoice_date": datetime.date.today(),
                    "batch_id": response_dict["batch_id"],
                    "state": "scheduled",
                    "is_payslip":True,
                }

                batch_id = self.env["batch.payment.tracking"].create(vals_list)
                rec.write(
                    {
                        "batch_id": response_dict["batch_id"],
                        "bambora_batch_payment_id": batch_id.id,
                        "state": 'waiting',
                    }
                )
        else:
            raise UserError(_("%s" % (response_dict['message'])))


    def write(self, vals):
        res = super(HrPayslipBatchPayment,self).write(vals)



    def send_bambora_refuse_mail(self):
        try:
            with_user = self.env['ir.config_parameter'].sudo()
            email_partner_ids = ast.literal_eval(with_user.get_param('syncoria_can_payroll.reminder_recipient_ids'))
            if email_partner_ids:
                email_partner_obj_ids = self.env['res.partner'].browse(email_partner_ids)
                email_ids = ','.join([i.email for i in email_partner_obj_ids])
                mail_template = self.env.ref('bambora_batch_payment.email_template_payroll_bambora_refuse')
                mail_template.send_mail(
                    self.id,

                    email_values={
                        'email_to': email_ids
                    },
                    force_send=True,

                )
        except Exception as e:
            _logger.warning(f"Email Not send.\n Exception{e}")



