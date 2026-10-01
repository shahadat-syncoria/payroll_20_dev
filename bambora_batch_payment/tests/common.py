###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import time

import odoo
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class BamboraEftCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_cad = cls.env.ref("base.CAD")
        cls.country_canada = cls.env.ref("base.ca")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.country_usa = cls.env.ref("base.us")

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

        # Banks: res.bank no longer exists in Odoo 20, bank name/BIC are stored on res.partner.bank
        cls.bank1 = {"bank_name": "Royal Bank of Canada", "bank_bic": "12773"}
        cls.bank2 = {"bank_name": "Bank of America", "bank_bic": "92773"}
        cls.bank3 = {"bank_name": "Bank of Montreal", "bank_bic": "12698"}
        cls.bank4 = {"bank_name": "Wells Fargo", "bank_bic": "11595"}

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
            "bambora_batch_payment.bamboraeft_vendor_journal"
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
                "bamboraeft_vendor_journal_id": cls.vendor_journal_id.id,
            }
        )


@odoo.tests.tagged("post_install", "-at_install")
class BamboraEftForm(BamboraEftCommon):
    def _create_tx(self, reference):
        return self.env["payment.transaction"].create(
            {
                "amount": 320.0,
                "provider_id": self.bamboraeft.id,
                "payment_method_id": self.env.ref(
                    "bambora_batch_payment.payment_method_bambora_eft"
                ).id,
                "currency_id": self.currency_cad.id,
                "reference": reference,
                "partner_id": self.buyer_id1,
                "partner_country_id": self.country_canada.id,
            }
        )

    def test_10_provider_setup(self):
        self.assertFalse(self.bamboraeft.is_live, "test without live environment")
        self.assertTrue(self.bamboraeft.support_tokenization)
        self.assertEqual(self.bamboraeft.code, "bamboraeft")

    def test_20_bamboraeft_payment_data_management(self):
        self.assertFalse(self.bamboraeft.is_live, "test without live environment")

        # typical data posted by bambora after the batch file has been received
        payment_data = {
            "code": 1,
            "message": "File successfully received",
            "batch_id": 10000347,
            "process_date": "20211129",
            "process_time_zone": "GMT-08:00",
            "batch_mode": "test",
            "reference": "SO004",
        }

        # unknown reference: no transaction found
        self.assertFalse(
            self.env["payment.transaction"]._search_by_reference("bamboraeft", payment_data)
        )

        tx = self._create_tx("SO004")
        found_tx = self.env["payment.transaction"]._search_by_reference(
            "bamboraeft", payment_data
        )
        self.assertEqual(found_tx, tx)

        # process it: a received batch leaves the transaction pending
        tx.with_context(payment_safe_write=True)._process(payment_data)
        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.provider_reference, str(payment_data["batch_id"]))

        # missing payment state
        tx2 = self._create_tx("SO004-2")
        with self.assertRaises(ValidationError):
            tx2.with_context(payment_safe_write=True)._process({"reference": "SO004-2"})
