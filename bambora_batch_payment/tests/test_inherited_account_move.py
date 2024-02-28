###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


import json

from odoo import fields
from odoo.tests.common import Form, TransactionCase


class TestInheritedAccountMove(TransactionCase):
    def setUp(self):
        super(TestInheritedAccountMove, self).setUp()

        self.currency_cad = self.env.ref("base.CAD")
        self.country_canada = self.env.ref("base.ca")
        self.currency_usd = self.env.ref("base.USD")
        self.country_usa = self.env.ref("base.us")
        # ==== Products ====
        self.product_a = self.env["product.product"].create(
            {
                "name": "product_a",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "lst_price": 1000.0,
                "standard_price": 800.0,
                # 'property_account_income_id': self.company_data['default_account_revenue'].id,
                # 'property_account_expense_id': self.company_data['default_account_expense'].id,
                # 'taxes_id': [(6, 0, self.tax_sale_a.ids)],
                # 'supplier_taxes_id': [(6, 0, self.tax_purchase_a.ids)],
            }
        )
        self.product_b = self.env["product.product"].create(
            {
                "name": "product_b",
                "uom_id": self.env.ref("uom.product_uom_dozen").id,
                "lst_price": 200.0,
                "standard_price": 160.0,
                # 'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
                # 'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
                # 'taxes_id': [(6, 0, (self.tax_sale_a + self.tax_sale_b).ids)],
                # 'supplier_taxes_id': [(6, 0, (self.tax_purchase_a + self.tax_purchase_b).ids)],
            }
        )
        # ========Create Partner ==========
        self.partner_values1 = self.env["res.partner"].create(
            {
                "name": "Patricia C Gregg",
                "lang": "en_US",
                "email": "patricia.gregg@example.com",
                "street": "3845 Fallon Drive",
                "street2": "2/543",
                "phone": "519-528-2978",
                "city": "Lucknow",
                "zip": "N0G 2H0",
                "country_id": self.country_canada.id,
            }
        )

        # ===== Create Invoice =======
        self.invoice = self.init_invoice(
            "in_invoice",
            post=True,
            products=self.product_a + self.product_b,
            partner=self.partner_values1,
        )

    def init_invoice(
        self,
        move_type,
        partner=None,
        invoice_date=None,
        post=False,
        products=[],
        amounts=[],
        taxes=None,
    ):
        move_form = Form(
            self.env["account.move"].with_context(
                default_move_type=move_type,
                account_predictive_bills_disable_prediction=True,
            )
        )
        move_form.invoice_date = invoice_date or fields.Date.from_string("2019-01-01")
        move_form.date = move_form.invoice_date
        if not partner.bank_account_count:
            partner.update(
                {
                    "bank_ids": [
                        (
                            0,
                            0,
                            {
                                "acc_number": "225566",
                                "bank_transit_no": "22668",
                                "bank_bic": "123",
                            },
                        )
                    ]
                }
            )
            # partner.bank_ids.acc_number = '2589631'
            # partner.bank_ids.bank_transit_no = '22668'
            # partner.bank_ids.bank_bic = '123'

        move_form.partner_id = partner

        # move_form.bambora_bank_identifier_number = '123'
        # move_form.bambora_bank_transit_number = '22668'
        # move_form.acc_number = '2589631'

        for product in products:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                if taxes:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(taxes)

        for amount in amounts:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = "test line"
                # We use account_predictive_bills_disable_prediction context key so that
                # this doesn't trigger prediction in case enterprise (hence account_predictive_bills) is installed
                line_form.price_unit = amount
                if taxes:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(taxes)

        rslt = move_form.save()

        if post:
            rslt.action_post()

        return rslt

    # ======================= For Vendor Invoice ======================
    def test_action_register_batch_vendor_complete_report(self):
        # resposnse = invoice.action_register_bambora_batch_payment()
        # with self.assertRaises(Exception) as context:
        self.invoice.partner_bank_id.bank_bic = "123"
        self.invoice.action_register_bambora_batch_payment()

        # ================== ALL TEST CASES =================
        #     try:
        #         if context.exception:
        #             self.assertNotEqual('Please Add Full Account Information for %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Please only sent posted entries!! %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('%s invoice Already Paid!!'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Bank identifier must be 3 digit and transit number is 5 digit!!. For %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Check Credentials !',context.exception.name,msg="UserError")
        #             self.assertNotEqual('Internal Error.',context.exception.name,msg="UserError")
        #     except:
        self.assertIsNotNone(self.invoice.bambora_batch_payment_id, msg="Not Pass")
        self.assertIsNotNone(self.invoice.batch_id, msg="Not Pass")
        self.assertIs(self.invoice.bambora_batch_state, "scheduled", msg="Not Pass")
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("*******************BAMBORA REGISTER TEST COMPLETE****************")

        print("*******************BAMBORA BATCH DATA UPDATE DONE****************")

        domain = [("code", "=", "bamboraeft")]
        domain += [("state", "!=", "disabled")]
        providers = self.env["payment.provider"].sudo().search(domain)
        bambora_batch_payment = self.invoice.bambora_batch_payment_id

        print("*******************Report API Completed Data ****************")

        test_response = (
            '{"response": {"version": "1.0", "code": 1, "message": "Report generated", "records": {"total": 0}, "record": [{"rowId": 0, "merchantId": 383610231, "batchId": %s, "transId": 761, "itemNumber": 1, "payeeName": "Deco Addict", "reference": "%s", "operationType": "D", "amount": 78750, "stateId": 2, "stateName": "Complete", "statusId": 1, "statusName": "Validated/Approved", "bankDescriptor": "", "messageId": "", "customerCode": "", "settlementDate": "2021-11-08", "returnedDate": "", "returnType": "", "eftId": 0}]}}'
            % (int(bambora_batch_payment.batch_id), self.invoice.name)
        )
        response_dict = json.loads(test_response)
        # bambora_batch = self.env["batch.payment.tracking"]
        self.invoice.bambora_batch_payment_id._batch_data_update(
            response_dict, providers
        )

        self.assertEqual(
            self.invoice.bambora_batch_payment_id.state, "complete", msg="Not Pass"
        )
        self.assertEqual(self.invoice.payment_state, "paid", msg="Not Pass")

        print("***********************************")

    def test_action_register_batch_vendor_reject_report(self):

        # resposnse = invoice.action_register_bambora_batch_payment()
        # with self.assertRaises(Exception) as context:
        self.invoice.partner_bank_id.bank_bic = "123"
        self.invoice.action_register_bambora_batch_payment()

        # ================== ALL TEST CASES =================
        #     try:
        #         if context.exception:
        #             self.assertNotEqual('Please Add Full Account Information for %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Please only sent posted entries!! %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('%s invoice Already Paid!!'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Bank identifier must be 3 digit and transit number is 5 digit!!. For %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Check Credentials !',context.exception.name,msg="UserError")
        #             self.assertNotEqual('Internal Error.',context.exception.name,msg="UserError")
        #     except:
        self.assertIsNotNone(self.invoice.bambora_batch_payment_id, msg="Not Pass")
        self.assertIsNotNone(self.invoice.batch_id, msg="Pass")
        self.assertIs(self.invoice.bambora_batch_state, "scheduled", msg="Not Pass")
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("*******************BAMBORA REGISTER TEST COMPLETE****************")

        print("*******************BAMBORA BATCH DATA UPDATE DONE****************")

        domain = [("code", "=", "bamboraeft")]
        domain += [("state", "!=", "disabled")]
        providers = self.env["payment.provider"].sudo().search(domain)
        bambora_batch_payment = self.invoice.bambora_batch_payment_id

        print("*******************Report API Cancel Data ****************")

        test_response = (
            '{"response": {"version": "1.0", "code": 1, "message": "Report generated", "records": {"total": 0}, "record": [{"rowId": 0, "merchantId": 383610231, "batchId": %s, "transId": 761, "itemNumber": 1, "payeeName": "Deco Addict", "reference": "%s", "operationType": "D", "amount": 78750, "stateId": 2, "stateName": "Rejected", "statusId": 1, "statusName": "Validated/Approved", "bankDescriptor": "", "messageId": "", "customerCode": "", "settlementDate": "2021-11-08", "returnedDate": "", "returnType": "", "eftId": 0}]}}'
            % (int(bambora_batch_payment.batch_id), self.invoice.name)
        )
        response_dict = json.loads(test_response)
        # bambora_batch = self.env["batch.payment.tracking"]
        self.invoice.bambora_batch_payment_id._batch_data_update(
            response_dict, providers
        )

        self.assertEqual(
            self.invoice.bambora_batch_payment_id.state, "rejected", msg="Not Pass"
        )
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("***********************************")

    # ======================= For Customer Invoice ======================
    def test_action_register_batch_customer_complete_report(self):
        self.invoice = self.init_invoice(
            "out_invoice",
            post=True,
            products=self.product_a + self.product_b,
            partner=self.partner_values1,
        )
        self.invoice.partner_bank_id.bank_bic = "123"
        self.invoice.action_register_bambora_batch_payment()

        # ================== ALL TEST CASES =================
        #     try:
        #         if context.exception:
        #             self.assertNotEqual('Please Add Full Account Information for %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Please only sent posted entries!! %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('%s invoice Already Paid!!'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Bank identifier must be 3 digit and transit number is 5 digit!!. For %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Check Credentials !',context.exception.name,msg="UserError")
        #             self.assertNotEqual('Internal Error.',context.exception.name,msg="UserError")
        #     except:
        self.assertIsNotNone(self.invoice.bambora_batch_payment_id, msg="Not Pass")
        self.assertIsNotNone(self.invoice.batch_id, msg="Not Pass")
        self.assertIs(self.invoice.bambora_batch_state, "scheduled", msg="Not Pass")
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("*******************BAMBORA REGISTER TEST COMPLETE****************")

        print("*******************BAMBORA BATCH DATA UPDATE DONE****************")

        domain = [("code", "=", "bamboraeft")]
        domain += [("state", "!=", "disabled")]
        providers = self.env["payment.provider"].sudo().search(domain)
        bambora_batch_payment = self.invoice.bambora_batch_payment_id

        print("*******************Report API Completed Data ****************")

        test_response = (
            '{"response": {"version": "1.0", "code": 1, "message": "Report generated", "records": {"total": 0}, "record": [{"rowId": 0, "merchantId": 383610231, "batchId": %s, "transId": 761, "itemNumber": 1, "payeeName": "Deco Addict", "reference": "%s", "operationType": "D", "amount": 78750, "stateId": 2, "stateName": "Complete", "statusId": 1, "statusName": "Validated/Approved", "bankDescriptor": "", "messageId": "", "customerCode": "", "settlementDate": "2021-11-08", "returnedDate": "", "returnType": "", "eftId": 0}]}}'
            % (int(bambora_batch_payment.batch_id), self.invoice.name)
        )
        response_dict = json.loads(test_response)
        # bambora_batch = self.env["batch.payment.tracking"]
        self.invoice.bambora_batch_payment_id._batch_data_update(
            response_dict, providers
        )

        self.assertEqual(
            self.invoice.bambora_batch_payment_id.state, "complete", msg="Not Pass"
        )
        self.assertEqual(self.invoice.payment_state, "paid", msg="Pass")

        print("***********************************")

    def test_action_register_batch_customer_reject_report(self):

        # resposnse = invoice.action_register_bambora_batch_payment()
        # with self.assertRaises(Exception) as context:
        self.invoice = self.init_invoice(
            "out_invoice",
            post=True,
            products=self.product_a + self.product_b,
            partner=self.partner_values1,
        )
        self.invoice.partner_bank_id.bank_bic = "123"
        self.invoice.action_register_bambora_batch_payment()

        # ================== ALL TEST CASES =================
        #     try:
        #         if context.exception:
        #             self.assertNotEqual('Please Add Full Account Information for %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Please only sent posted entries!! %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('%s invoice Already Paid!!'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Bank identifier must be 3 digit and transit number is 5 digit!!. For %s'%invoice.name ,context.exception.name,msg="UserError")
        #             self.assertNotEqual('Check Credentials !',context.exception.name,msg="UserError")
        #             self.assertNotEqual('Internal Error.',context.exception.name,msg="UserError")
        #     except:
        self.assertIsNotNone(self.invoice.bambora_batch_payment_id, msg="Not Pass")
        self.assertIsNotNone(self.invoice.batch_id, msg="Pass")
        self.assertIs(self.invoice.bambora_batch_state, "scheduled", msg="Not Pass")
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("*******************BAMBORA REGISTER TEST COMPLETE****************")

        print("*******************BAMBORA BATCH DATA UPDATE DONE****************")

        domain = [("code", "=", "bamboraeft")]
        domain += [("state", "!=", "disabled")]
        providers = self.env["payment.provider"].sudo().search(domain)
        bambora_batch_payment = self.invoice.bambora_batch_payment_id

        print("*******************Report API Cancel Data ****************")

        test_response = (
            '{"response": {"version": "1.0", "code": 1, "message": "Report generated", "records": {"total": 0}, "record": [{"rowId": 0, "merchantId": 383610231, "batchId": %s, "transId": 761, "itemNumber": 1, "payeeName": "Deco Addict", "reference": "%s", "operationType": "D", "amount": 78750, "stateId": 2, "stateName": "Rejected", "statusId": 1, "statusName": "Validated/Approved", "bankDescriptor": "", "messageId": "", "customerCode": "", "settlementDate": "2021-11-08", "returnedDate": "", "returnType": "", "eftId": 0}]}}'
            % (int(bambora_batch_payment.batch_id), self.invoice.name)
        )
        response_dict = json.loads(test_response)
        # bambora_batch = self.env["batch.payment.tracking"]
        self.invoice.bambora_batch_payment_id._batch_data_update(
            response_dict, providers
        )

        self.assertEqual(
            self.invoice.bambora_batch_payment_id.state, "rejected", msg="Not Pass"
        )
        self.assertEqual(self.invoice.payment_state, "not_paid", msg="Not Pass")

        print("***********************************")
