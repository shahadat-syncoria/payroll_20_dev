###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import time

import odoo
from lxml import objectify
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class BamboraEftCommon(TransactionCase):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_cad = cls.env.ref("base.CAD")
        cls.country_canada = cls.env.ref("base.ca")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.country_usa = cls.env.ref("base.USD")

        # 1:Canadian
        # dict partner values
        cls.buyer_values1 = {
            "partner_name": "Patricia C Gregg",
            "partner_lang": "en_US",
            "partner_email": "patricia.gregg@example.com",
            "partner_address": "3845 Fallon Drive",
            "partner_phone": "519-528-2978",
            "partner_city": "Lucknow",
            "partner_zip": "N0G 2H0",
            "partner_country": cls.country_canada,
            "partner_country_id": cls.country_canada.id,
            "partner_country_name": "Canada",
            "billing_partner_name": "Patricia C Gregg",
            "billing_partner_commercial_company_name": "Gamma Gas",
            "billing_partner_lang": "en_US",
            "billing_partner_email": "patricia.gregg@example.com",
            "billing_partner_address": "3845 Fallon Drive",
            "billing_partner_phone": "519-528-2978",
            "billing_partner_city": "Lucknow",
            "billing_partner_zip": "N0G 2H0",
            "billing_partner_country": cls.country_canada,
            "billing_partner_country_id": cls.country_canada.id,
            "billing_partner_country_name": "Canada",
        }

        cls.buyer1 = cls.env["res.partner"].create(
            {
                "name": "Patricia C Gregg",
                "lang": "en_US",
                "email": "patricia.gregg@example.com",
                "street": "3845 Fallon Drive",
                "street2": "2/543",
                "phone": "519-528-2978",
                "city": "Lucknow",
                "zip": "N0G 2H0",
                "country_id": cls.country_canada.id,
            }
        )
        cls.buyer_id1 = cls.buyer1.id

        # 2:American
        # dict partner values
        cls.buyer_values2 = {
            "partner_name": "William R Wilson",
            "partner_lang": "en_US",
            "partner_email": "william.wilson@example.com",
            "partner_address": "1771 Lynden Road",
            "partner_phone": "905-584-6038",
            "partner_city": "Caledon East",
            "partner_zip": "L0N 1E0",
            "partner_country": cls.country_usa,
            "partner_country_id": cls.country_usa.id,
            "partner_country_name": "United States",
            "billing_partner_name": "William R Wilson",
            "billing_partner_commercial_company_name": "Omni Tech Solutions",
            "billing_partner_lang": "en_US",
            "billing_partner_email": "patricia.gregg@example.com",
            "billing_partner_address": "1771 Lynden Road",
            "billing_partner_phone": "905-584-6038",
            "billing_partner_city": "Caledon East",
            "billing_partner_zip": "L0N 1E0",
            "billing_partner_country": cls.country_usa,
            "billing_partner_country_id": cls.country_usa.id,
            "billing_partner_country_name": "United States",
        }

        # test partner
        cls.buyer2 = cls.env["res.partner"].create(
            {
                "name": "William R Wilson",
                "lang": "en_US",
                "email": "william.wilson@example.com",
                "street": "3647 portage ave unit c1a",
                "street2": "",
                "phone": "204-584-6038",
                "city": "Winnipeg",
                "zip": "R3K 2G6",
                "country_id": cls.country_usa.id,
                # WinniPeg,Manitoba
            }
        )
        cls.buyer_id2 = cls.buyer2.id

        # 3:Canadian
        # dict partner values
        cls.buyer_values3 = {
            "partner_name": "Jeffrey K Davis",
            "partner_lang": "en_US",
            "partner_email": "jeffrey.davis@example.com",
            "partner_address": "934 rue des Églises Est",
            "partner_phone": "418-585-4625",
            "partner_city": "Schefferville",
            "partner_zip": "J0C 1G0",
            "partner_country": cls.country_canada,
            "partner_country_id": cls.country_canada.id,
            "partner_country_name": "Canada",
            "billing_partner_name": "Jeffrey K Davis",
            "billing_partner_commercial_company_name": "Coconut",
            "billing_partner_lang": "en_US",
            "billing_partner_email": "jeffrey.davis@example.com",
            "billing_partner_address": "934 rue des Églises Est",
            "billing_partner_phone": "418-585-4625",
            "billing_partner_city": "Schefferville",
            "billing_partner_zip": "J0C 1G0",
            "billing_partner_country": cls.country_canada,
            "billing_partner_country_id": cls.country_canada.id,
            "billing_partner_country_name": "Canada",
        }

        # test partner
        cls.buyer3 = cls.env["res.partner"].create(
            {
                "name": "Jeffrey K Davis",
                "lang": "en_US",
                "email": "jeffrey.davis@example.com",
                "street": "934 rue des Églises Est",
                "street2": "",
                "phone": "418-585-4625",
                "city": "Schefferville",
                "zip": "J0C 1G0",
                "country_id": cls.country_canada.id,
            }
        )
        cls.buyer_id3 = cls.buyer3.id

        # 4:American
        # dict partner values
        cls.buyer_values4 = {
            "partner_name": "Beverly G Tessier",
            "partner_lang": "en_US",
            "partner_email": "beverly.tessier@example.com",
            "partner_address": "4864 Duffy Street",
            "partner_phone": "219-734-9799",
            "partner_city": "Portage",
            "partner_zip": "46383",
            "partner_country": cls.country_usa,
            "partner_country_id": cls.country_usa.id,
            "partner_country_name": "United States",
            "billing_partner_name": "Beverly G Tessier",
            "billing_partner_commercial_company_name": "Omni Tech Solutions",
            "billing_partner_lang": "en_US",
            "billing_partner_email": "beverly.tessier@example.com",
            "billing_partner_address": "4864 Duffy Street",
            "billing_partner_phone": "219-734-9799",
            "billing_partner_city": "Portage",
            "billing_partner_zip": "46383",
            "billing_partner_country": cls.country_usa,
            "billing_partner_country_id": cls.country_usa.id,
            "billing_partner_country_name": "United States",
        }

        # test partner
        cls.buyer4 = cls.env["res.partner"].create(
            {
                "name": "Beverly G Tessier",
                "lang": "en_US",
                "email": "beverly.tessier@example.com",
                "street": "4864 Duffy Street",
                "street2": "",
                "phone": "219-734-9799",
                "city": "Portage",
                "zip": "46383",
                "country_id": cls.country_usa.id,
            }
        )
        cls.buyer_id4 = cls.buyer4.id

        # Banks:
        cls.bank1 = cls.env["res.bank"].create(
            {
                "name": "Royal Bank of Canada",
                "bic": "12773",
                "email": "rbc@ca.com",
                "street": "200 Bay St. Main Floor,",
                "street2": "RBC Dominion Securities",
                "phone": "416-974-3940",
                "city": "Toronto",
                "zip": "M5J 2J5",
                "country_id": cls.country_canada.id,
            }
        )

        cls.bank2 = cls.env["res.bank"].create(
            {
                "name": "Bank of America",
                "bic": "92773",
                "email": "rbc@ca.com",
                "street": "150 Broadway",
                "street2": "",
                "phone": "(212) 406-0475)",
                "city": "New York",
                "zip": "10038",
                "country_id": cls.country_usa.id,
            }
        )

        cls.bank3 = cls.env["res.bank"].create(
            {
                "name": "Bank of Montreal",
                "bic": "12698",
                "email": "bom@ca.com",
                "street": "3647 portage ave unit c1a",
                "street2": "",
                "phone": "(204) 985-2025)",
                "city": "Winnipeg",
                "zip": "R3K 2G6",
                "country_id": cls.country_canada.id,
            }
        )

        cls.bank4 = cls.env["res.bank"].create(
            {
                "name": "Wells Fargo",
                "bic": "11595",
                "email": "wellfargo@usatest.com",
                "street": "7900 Moorsbridge Rd",
                "street2": "",
                "phone": "(269) 323-4800",
                "city": "Portage",
                "zip": "49024",
                "country_id": cls.country_usa.id,
            }
        )

        # Adding Demo Data
        cls.bank_account_1 = ("Patricia C Gregg", "00001", "Canadian", "127", "12773")
        cls.bank_account_2 = ("William R Wilson", "99901", "American", "927", "92773")
        cls.bank_account_3 = ("Jeffrey K Davis", "00002", "Canadian", "154", "12698")
        cls.bank_account_4 = ("Beverly G Tessier", "99902", "American", "687", "11595")

        cls.bamboraeft = cls.env.ref(
            "bambora_batch_payment.payment_provider_bamboraeft"
        )
        cls.journal_id = cls.env.ref(
            "bambora_batch_payment.bamboraeft_customer_journal"
        )
        cls.vendor_journal_id = cls.env.ref(
            "bambora_batch_payment.bamboraeft_vendor_journal_id"
        )
        cls.bamboraeft.write(
            {
                "bamboraeft_merchant_id": "383610231",
                "bamboraeft_batch_api": "59346692ed194CD1805A66f541287B74",
                "bamboraeft_report_api": "AF492A390B00481CbD4a2907FA33e3ed",
                "bamboraeft_payment_api": "9F0F1cE3EA9541489656E0d2470F5285",
                "bamboraeft_profile_api": "5B94D0E7290D4D33953BD12EE6B467A4",
                "bamboraeft_create_profile": True,
                "journal_id": cls.journal_id.id,
                "vendor_journal_id": cls.vendor_journal_id.id,
            }
        )


@odoo.tests.tagged("post_install", "-at_install", "-standard", "external")
class BamboraEftForm(BamboraEftCommon):
    def test_10_bamboraeft_form_render(self):
        self.assertEqual(self.bamboraeft.state, "test", "test without test environment")
        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        print("Test: button direct rendering")
        self.env["ir.config_parameter"].get_param("web.base.url")
        form_values = {
            "data_set": "/payment/bamboraeft/s2s/create_json_3ds",
            "x_amount": "56.16",
            "provider_id": self.bamboraeft.id,
            "provider_state": self.bamboraeft.state,
            "bamboraeft_merchant_id": self.bamboraeft.bamboraeft_merchant_id,
            "bamboraeft_batch_api": self.bamboraeft.bamboraeft_batch_api,
            "bamboraeft_report_api": self.bamboraeft.bamboraeft_report_api,
            "bamboraeft_payment_api": self.bamboraeft.bamboraeft_payment_api,
            "bamboraeft_profile_api": self.bamboraeft.bamboraeft_profile_api,
            # 'request': request,
            # 'csrf_token': request.csrf_token(),
            "return_url": "5B94D0E7290D4D33953BD12EE6B467A4",
            "partner_id": self.cls.buyer_id1.id,
            # 'order_id': request.httprequest,
            "window_href": str(int(time.time())),
            "data_key": "",
            "charge_total": "56.16",
            "order_name": None,
            "note": None,
            "email": self.cls.buyer_id1.email,
            # 'bamboraTran': 'Norbert',
            "bank_name": "Royal Bank of Canada",
            "acc_holder_name": "Patricia C Gregg",
            "acc_number": "00001",
            "bank_account_type": "Canadian",
            "institution_number": "12773",
            "branch_number": "127",
        }

        # render the button
        res = self.bamboraeft.render(
            "SO004", 56.16, self.currency_ca.id, values=self.buyer_values1
        )
        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(
            len(data_set),
            1,
            'Bambora EFT: Found %d "data_set" input instead of 1' % len(data_set),
        )
        # self.assertEqual(data_set[0].get('data-action-url'), 'https://test.bamboraeft.net/gateway/transact.dll', 'bamboraeft: wrong data-action-url POST url')
        # for el in tree.iterfind('input'):
        #     values = list(el.attrib.values())
        #     if values[1] in ['submit', 'return_url', 'data_set']:
        #         continue
        #     self.assertEqual(
        #         values[2],
        #         form_values[values[1]],
        #         'bamboraeft: wrong value for input %s: received %s instead of %s' % (values[1], values[2], form_values[values[1]])
        #     )

    @mute_logger("odoo.addons.bambora_batch_payment.models.payment", "ValidationError")
    def test_20_bamboraeft_form_management(self):
        # be sure not to do stupid thing
        print("Test: test_20_bamboraeft_form_management")
        self.assertEqual(self.bamboraeft.state, "test", "test without test environment")

        # typical data posted by bamboraeft after client has successfully paid
        bamboraeft_post_data = {
            "code": 1,
            "message": "File successfully received",
            "batch_id": 10000347,
            "process_date": "20211129",
            "process_time_zone": "GMT-08:00",
            "batch_mode": "test",
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"].form_feedback(
                bamboraeft_post_data, "bamboraeft"
            )

        tx = self.env["payment.transaction"].create(
            {
                "amount": 320.0,
                "provider_id": self.bamboraeft.id,
                "currency_id": self.currency_cad.id,
                "reference": "SO004",
                "partner_name": "Patricia C Gregg",
                "partner_country_id": self.country_canada.id,
            }
        )

        # validate it
        self.env["payment.transaction"].form_feedback(
            bamboraeft_post_data, "bamboraeft"
        )
        # check state
        self.assertEqual(
            tx.state, "done", "bamboraeft: validation did not put tx into done state"
        )
        self.assertEqual(
            tx.provider_reference,
            bamboraeft_post_data.get("x_trans_id"),
            "bamboraeft: validation did not update tx payid",
        )

        tx = self.env["payment.transaction"].create(
            {
                "amount": 320.0,
                "providerid": self.bamboraeft.id,
                "currency_id": self.currency_cad.id,
                "reference": "SO004-2",
                "partner_name": "Patricia C Gregg",
                "partner_country_id": self.country_canada.id,
            }
        )

        # simulate an error
        self.env["payment.transaction"].form_feedback(
            bamboraeft_post_data, "bamboraeft"
        )
        # check state
        self.assertNotEqual(
            tx.state,
            "done",
            "bamboraeft: erroneous validation did put tx into done state",
        )


@odoo.tests.tagged("post_install", "-at_install", "-standard")
class BamboraEftS2s(BamboraEftCommon):
    def test_30_bamboraeft_s2s(self):
        print("Test: test_30_bamboraeft_s2s")
        # be sure not to do stupid thing
        bamboraeft = self.bamboraeft
        self.assertEqual(bamboraeft.state, "test", "test without test environment")

        # add credential
        # FIXME: put this test in master-nightly on odoo/odoo + create sandbox account
        journal_id = self.env.ref("bambora_batch_payment.bamboraeft_customer_journal")
        vendor_journal_id = self.env.ref(
            "bambora_batch_payment.bamboraeft_vendor_journal_id"
        )

        bamboraeft.write(
            {
                "bamboraeft_merchant_id": "383610231",
                "bamboraeft_batch_api": "59346692ed194CD1805A66f541287B74",
                "bamboraeft_report_api": "AF492A390B00481CbD4a2907FA33e3ed",
                "bamboraeft_payment_api": "9F0F1cE3EA9541489656E0d2470F5285",
                "bamboraeft_profile_api": "5B94D0E7290D4D33953BD12EE6B467A4",
                "bamboraeft_create_profile": True,
                "journal_id": "5B94D0E7290D4D33953BD12EE6B467A4",
            }
        )
        bamboraeft.write(
            {
                "bamboraeft_merchant_id": "383610231",
                "bamboraeft_batch_api": "59346692ed194CD1805A66f541287B74",
                "bamboraeft_report_api": "AF492A390B00481CbD4a2907FA33e3ed",
                "bamboraeft_payment_api": "9F0F1cE3EA9541489656E0d2470F5285",
                "bamboraeft_profile_api": "5B94D0E7290D4D33953BD12EE6B467A4",
                "bamboraeft_create_profile": True,
                "journal_id": journal_id.id,
                "vendor_journal_id": vendor_journal_id.id,
            }
        )

        # self.assertTrue(bamboraeft.bamboraeft_test_credentials, 'bamboraeft.net: s2s authentication failed')#NA

        # create payment meethod
        payment_token = self.env["payment.token"].create(
            {
                "providerid": bamboraeft.id,
                "partner_id": self.buyer_id1,
                "bambora_token_type": "permanent",
                "bambora_token": "A22651A33D824A3990ddC10287290ef0",
                "code": "bamboraeft",
                "providerref": "bamboraeft",
                "name": "***1901 (EFT)",
            }
        )

        # create normal s2s transaction
        transaction = self.env["payment.transaction"].create(
            {
                "amount": 500,
                "providerid": bamboraeft.id,
                "type": "server2server",
                "currency_id": self.currency_canada.id,
                "reference": "test_ref_%s" % int(time.time()),
                "payment_token_id": payment_token.id,
                "partner_id": self.buyer_id1,
            }
        )
        transaction.bamboraeft_s2s_do_transaction()
        self.assertEqual(
            transaction.state,
            "done",
        )

        # switch to 'bamboraeft only'
        # create bamboraeft only s2s transaction & capture it
        self.bamboraeft.capture_manually = True
        transaction = self.env["payment.transaction"].create(
            {
                "amount": 500,
                "providerid": bamboraeft.id,
                "type": "server2server",
                "currency_id": self.currency_canada.id,
                "reference": "test_ref_%s" % int(time.time()),
                "payment_token_id": payment_token.id,
                "partner_id": self.buyer_id1,
            }
        )
        transaction.bamboraeft_s2s_do_transaction()
        self.assertEqual(transaction.state, "bamboraeftd")
        transaction.action_capture()
        self.assertEqual(transaction.state, "done")

        # create bamboraeft only s2s transaction & void it
        self.bamboraeft.capture_manually = True
        transaction = self.env["payment.transaction"].create(
            {
                "amount": 500,
                "providerid": bamboraeft.id,
                "type": "server2server",
                "currency_id": self.currency_canada.id,
                "reference": "test_ref_%s" % int(time.time()),
                "payment_token_id": payment_token.id,
                "partner_id": self.buyer_id1,
            }
        )
        transaction.bamboraeft_s2s_do_transaction()
        self.assertEqual(transaction.state, "bamboraeftd")
        transaction.action_void()
        self.assertEqual(transaction.state, "cancel")

        # try charging an unexisting profile
        ghost_payment_token = payment_token.copy()
        ghost_payment_token.bamboraeft_profile = "99999999999"
        # create normal s2s transaction
        transaction = self.env["payment.transaction"].create(
            {
                "amount": 500,
                "providerid": bamboraeft.id,
                "type": "server2server",
                "currency_id": self.currency_canada.id,
                "reference": "test_ref_%s" % int(time.time()),
                "@tagged": ghost_payment_token.id,
                "partner_id": self.buyer_id1,
            }
        )
        transaction.bamboraeft_s2s_do_transaction()
        self.assertEqual(transaction.state, "cancel")
