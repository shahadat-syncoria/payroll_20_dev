from odoo import fields, models, _, api
from ..helper.helper_functions import year_selection


class TaxSlabConfiguration(models.Model):
    _name = 'tax.slab'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tax Slab Configuration'
    _rec_name = 'name'



    name = fields.Char(string="Reference Name")
    slab_year = fields.Selection(
        year_selection,
        string="Year",
        default='2023'
    )

    # ========================== CPP ============================
    cpp_max_an_pen_earn = fields.Float(string="Maximum Annual Pensionable Earnings")
    cpp_basic_exem = fields.Float(string="Basic Exemption Amount")
    cpp_max_con_earn = fields.Float(string="Maximum Contributory Earnings")
    cpp_emp_employ_rate = fields.Float(string="Employee & Employer Contribution Rate (%)",digits=(6,4))
    cpp_emp_employ_contrib = fields.Float(string="Maximum Annual Employee & Employer Contribution")

    # ========================== CPP2 ============================
    cpp2_add_max_an_pen_earn = fields.Float(string="Additional Maximum Annual Pensionable Earnings")
    cpp2_emp_employ_rate = fields.Float(string="CPP2 Employee & Employer Contribution Rate (%)", digits=(6, 4))
    cpp2_emp_employ_contrib = fields.Float(string="CPP2 Maximum Annual Employee & Employer Contribution")
    cpp2_self_employed_contrib = fields.Float(string="Maximum Annual Self-employed Contribution")

    # =========================== EI ================================
    ei_max_an_pen_earn = fields.Float(string="Maximum Annual Insurable Earnings")
    ei_rate = fields.Float(string="Rate (%)",digits=(6,4))
    ei_employer_rate = fields.Float(string="Employer Rate (%)",digits=(6,4))
    ei_max_emp_anu_prem = fields.Float(string="Maximum Annual Employee Premium")
    ei_max_employer_anu_prem = fields.Float(string="Maximum Annual Employer Premium")

    # =========================== FED Tax ================================
    fed_tax_line_ids = fields.One2many(
        comodel_name='fed.tax',
        inverse_name='tax_slab_id',
        string='Fed Taxes',
        required=False)

    # =========================== Prov Tax ================================
    prov_tax_line_ids = fields.One2many(
        comodel_name='prov.tax',
        inverse_name='tax_slab_id',
        string='Provincial Taxes',
        required=False)


class FedTax(models.Model):
    _name = "fed.tax"
    _description = "Canada Fed Tax Configuration"



    year = fields.Selection(
        string="Year",
        related='tax_slab_id.slab_year',
        store=True
    )
    salary_from = fields.Float(string='Salary From', index=True)
    salary_to = fields.Float(string='Salary To', index=True)
    tax_category = fields.Selection([
        ('CC0', 'CC0'),
        ('CC1', 'CC 1'),
        ('CC2', 'CC 2'),
        ('CC3', 'CC 3'),
        ('CC4', 'CC 4'),
        ('CC5', 'CC 5'),
        ('CC6', 'CC 6'),
        ('CC7', 'CC 7'),
        ('CC8', 'CC 8'),
        ('CC9', 'CC 9'),
        ('CC10', 'CC 10'),
    ], string='Tax Claim Code Category', index=True)
    tax_amount = fields.Float(string='Tax Amount')
    tax_slab_id = fields.Many2one('tax.slab')
    pay_cycle = fields.Selection([
        ('52', '52'),
        ('26', '26'),
        ('24', '24'),
        ('12', '12'),
    ], default='12', string="Pay Cycle")

    # @api.model
    def get_tax_amount(self, salary, tax_category, year,pay_cycle):
        cache_key = (salary, tax_category, year)
        # cache = self.env.cache
        # result = cache.get(cache_key)

        # if result is None:
        domain = [
            ('salary_from', '<=', salary),
            ('salary_to', '>', salary),
            ('pay_cycle', '=', pay_cycle),
            ('tax_category', '=', tax_category),
            ('year', '=', year)
        ]
        record = self.search(domain, limit=1)
        result = record.tax_amount if record else 0.0

            # cache.set(cache_key, result)

        return result

class ProvTax(models.Model):
    _name = "prov.tax"
    _description = "Canada Provincial Tax Configuration"


    year = fields.Selection(
        string="Year",
        related='tax_slab_id.slab_year',
        store=True
    )
    salary_from = fields.Float(string='Salary From', index=True)
    salary_to = fields.Float(string='Salary To', index=True)
    tax_category = fields.Selection([
        ('CC0', 'CC0'),
        ('CC1', 'CC 1'),
        ('CC2', 'CC 2'),
        ('CC3', 'CC 3'),
        ('CC4', 'CC 4'),
        ('CC5', 'CC 5'),
        ('CC6', 'CC 6'),
        ('CC7', 'CC 7'),
        ('CC8', 'CC 8'),
        ('CC9', 'CC 9'),
        ('CC10', 'CC 10'),
    ], string='Tax Claim Code Category', index=True)
    tax_amount = fields.Float(string='Tax Amount')
    tax_slab_id = fields.Many2one('tax.slab')
    pay_cycle = fields.Selection([
        ('52', '52'),
        ('26', '26'),
        ('24', '24'),
        ('12', '12'),
    ], default='12', string="Pay Cycle")

    # @api.model
    def get_tax_amount(self, salary, tax_category, year,pay_cycle):
        # cache_key = (salary, tax_category, year)
        # cache = self.env.cache
        # result = cache.get(cache_key)

        # if result is None:
        domain = [
            ('salary_from', '<=', salary),
            ('salary_to', '>', salary),
            ('pay_cycle', '=', pay_cycle),
            ('tax_category', '=', tax_category),
            ('year', '=', year)
        ]
        record = self.search(domain, limit=1)
        result = record.tax_amount if record else 0.0

            # cache.set(cache_key, result)

        return result
