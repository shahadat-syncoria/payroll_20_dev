from odoo import fields, models, api, _
from odoo.exceptions import UserError

EMPLOYMENT_CODE = [
    ('11', "Placement or employment agency workers"),
    ('12', "Drivers of taxis or other passenger-carrying vehicles"),
    ('13', "Barbers or hairdressers"),
    ('14', "Withdrawal from a prescribed salary deferral arrangement plan"),
    ('15', "Seasonal Agricultural Workers Program"),
    ('16', "Detached employee - Social security agreement."),
    ('17', "Fishers - Self-employed"),
]

deduction_amount_type = [
    ("percent","%"),
    ("fixed","CAD"),
]


class InheritedResPartner(models.Model):
    _inherit = 'hr.version'

    is_cpp_qpp_xmpt_cd = fields.Boolean(string="Canada Pension Plan or Quebec Pension Plan Exempt", default=False)
    is_ei_xmpt_cd = fields.Boolean(string="Employment Insurance Exempt", default=False)
    is_prov_pip_xmpt_cd = fields.Boolean(string="PPIP Exempt", default=False)
    employee_empt_cd = fields.Selection(selection=EMPLOYMENT_CODE, string="Employment Code", help="- T4 slip, box 29\
        - Do not complete Box 14 - Employment income, if you are using employment codes 11, 12, 13, or 17.\
        11 - Placement or employment agency workers\
        12 - Drivers of taxis or other passenger-carrying vehicles\
        13 - Barbers or hairdressers\
        14 - Withdrawal from a prescribed salary deferral arrangement plan\
        15 - Seasonal Agricultural Workers Program\
        16 - Detached employee - Social security agreement.\
        Note: When CPP is paid by the employer on behalf of detached employees under employment code 16, box 14 is left blank if no other type of income is reported. Boxes 16 and 26 are completed with the appropriate amounts and boxes 18 and 24 are left blank.\
        17 - Fishers - Self-employed")

    federal_amount_from_td1 = fields.Float(string="Federal Amount From TD1")
    proviancial_amount_from_td1 = fields.Float(string="Provincial Amount From TD1")

    federal_claim_code_from_td1 = fields.Selection([
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
    ], string="Federal Claim Code From TD1")

    provincial_claim_code_from_td1 = fields.Selection([
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
    ], string="Provincial Claim Code From TD1")

    deductions = fields.Many2one('tax.slab', string='Payroll Deductions',
                                 default=lambda self: self.env['tax.slab'].search([], limit=1))

    salary_pay_cycle = fields.Many2one('paycycle.config',
                                       string='Salary Pay Cycle',
                                       tracking=True,
                                       help="For default value leave blank", )
    # ========================= Hourly Configuration =======================
    is_hourly = fields.Boolean(string="Is Hourly?", compute="_compute_is_hourly", store=True)
    is_fixed = fields.Boolean(string="Is Fixed Salary?", default=True,help="Salary will be fixed according to Pay cycle wage regardless worked hour")

    paycycle_wage = fields.Float(string="Pay Cycle Wage", tracking=True)

    # =========================== Deductions ===================================
    rrsp_amount = fields.Float("Employee Portion")
    rrsp_type = fields.Selection(deduction_amount_type,default="percent")

    employer_rrsp = fields.Float("Employer Portion")
    employer_rrsp_type = fields.Selection(deduction_amount_type, default="percent")

    rrsp_amount_withdraw = fields.Boolean("Can Employee Withdraw RRSP before retirement?")

    garnishment = fields.Boolean("Garnishment Deduction?",default=False)
    wage_garnishment = fields.Integer("Wage Garnishment",help="It involves the employer withholding a portion of an employee's wages to satisfy a debt.")
    wage_garnishment_type = fields.Selection(deduction_amount_type,default="percent")

    bank_garnishment = fields.Integer("Bank Account Garnishment",
                                      help="It involves involves the creditor obtaining a court order to seize funds "
                                           "from the debtor's bank account.")
    bank_garnishment_type = fields.Selection(deduction_amount_type, default="percent")

    alimony_garnishment = fields.Integer("Spousal Support or Alimony Garnishment",
                                      help="A court may order the garnishment of wages to ensure that spousal support or alimony payments are made.")
    alimony_garnishment_type = fields.Selection(deduction_amount_type, default="percent")

    child_support_garnishment = fields.Integer("Child Support Garnishment",
                                         help="A court may order the garnishment of wages to ensure that spousal support or alimony payments are made.")
    child_support_garnishment_type = fields.Selection(deduction_amount_type, default="percent")

    # =========================== Benefit Plans ===================================
    benefit_plans = fields.Boolean("Benefit Plans",default=False)


    life_insurance = fields.Float("Employee Portion")
    life_insurance_type = fields.Selection(deduction_amount_type, default="percent")
    life_insurance_employer = fields.Float("Employer Portion")
    life_insurance_employer_type = fields.Selection(deduction_amount_type, default="percent")

    medical_insurance = fields.Float("Employee Portion")
    medical_insurance_type = fields.Selection(deduction_amount_type, default="percent")
    medical_insurance_employer = fields.Float("Employer Portion")
    medical_insurance_employer_type = fields.Selection(deduction_amount_type, default="percent")

    # To get the paycycle of the employee from its structure_type_id if the paycycle is not selected.
    @api.model_create_multi
    def create(self, vals_list):

        res = super(InheritedResPartner, self).create(vals_list)
        for contract in res:
            try:
                if not contract.salary_pay_cycle:
                    paycycle = contract.structure_type_id.default_pay_cycle
                    if contract.structure_type_id.default_struct_id and contract.structure_type_id.default_struct_id.structure_pay_cycle:
                        paycycle = contract.structure_type_id.default_struct_id.structure_pay_cycle
                    contract.salary_pay_cycle = paycycle
            except:
                pass
        return res

    def write(self, vals):
        if 'structure_type_id' in vals:
            structure_type_ids = self.structure_type_id.browse(vals['structure_type_id'])
            try:
                if structure_type_ids:
                    paycycle = structure_type_ids.default_pay_cycle
                    if structure_type_ids.default_struct_id and structure_type_ids.default_struct_id.structure_pay_cycle:
                        paycycle = structure_type_ids.default_struct_id.structure_pay_cycle
                    vals['salary_pay_cycle'] = paycycle.id
            except:
                pass
        return super(InheritedResPartner, self).write(vals)


    # ========================= Hourly Configuration ===============

    @api.onchange("paycycle_wage")
    def _onchange_wage(self):
        for rec in self:
            if rec.paycycle_wage:
                rec.wage = (rec.paycycle_wage * int(rec.salary_pay_cycle.pay_cycle or rec.structure_type_id.default_pay_cycle.pay_cycle)) / 12
            else:
                rec.wage = 0.0

    @api.onchange("hourly_wage")
    def _onchange_hourly_wage(self):
        for rec in self:
            if rec.hourly_wage:
                rec.hourly_wage = rec.hourly_wage
            else:
                rec.hourly_wage = 0.0
    @api.depends("wage_type")
    def _compute_is_hourly(self):
        for rec in self:
            if rec.wage_type == "hourly":
                rec.is_hourly = True
            else:
                rec.is_hourly = False


    @api.constrains('hourly_wage')
    def _constraint_hourly_rate(self):
        for rec in self:
            if rec.is_hourly and rec.hourly_wage <= 0.0:
                raise UserError("Hourly Rate should be greater than 0.")

    # @api.depends('structure_type_id')
    # def _compute_paycycle(self):
    #     try:
    #         paycycle = None
    #         if self.structure_type_id:
    #             paycycle = self.structure_type_id.default_pay_cycle
    #             if self.structure_type_id.default_struct_id:
    #                 paycycle = self.structure_type_id.default_struct_id.structure_pay_cycle
    #         self.salary_pay_cycle = paycycle
    #     except:
    #         pass
