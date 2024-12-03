from odoo.exceptions import UserError
from odoo import models, api, fields, _
from datetime import datetime
from ..helper.helper_functions import year_selection

CODE = [
    ('0', '0'),
    ('1', '1'),
]

# old code need to remove
def get_years():
    current_year = datetime.now().year
    start_year = current_year - 3  # 3 years before the current year
    end_year = current_year + 7  # 7 years after the current year
    return [(str(year), str(year)) for year in range(start_year, end_year + 1)]


EMPLOYMENT_CODE = [
    ('11', "Placement or employment agency workers"),
    ('12', "Drivers of taxis or other passenger-carrying vehicles"),
    ('13', "Barbers or hairdressers"),
    ('14', "Withdrawal from a prescribed salary deferral arrangement plan"),
    ('15', "Seasonal Agricultural Workers Program"),
    ('16', "Detached employee - Social security agreement."),
    ('17', "Fishers - Self-employed"),
]

class InhertitedHrEmployee(models.Model):
    _inherit = 'hr.employee'

    _sql_constraints = [
        ('identification_id_len', 'CHECK (LENGTH(identification_id) = 9)', ('Social Insurance Number Must be of 9 digits.')),
        # ('registration_number_verification', 'CHECK (registration_number SIMILAR TO ^[178][0-9]{8}(RP|RW)[0-9]{4}$)', ('Payroll Account Number Must Match patterns.')),
    ]

    is_portal_user = fields.Boolean()
    portal_user_id = fields.Many2one("res.users")
    is_vacation_pay_carry_over = fields.Boolean(default=True, string='Vacation Pay Carry Over?')
    payroll_line_ids = fields.One2many('hr.employee.ytd.payroll.information', 'head_id')
    
    employee_prpp_dpsp_rgst_nbr = fields.Integer(string="RPP or DPSP Registration Number Registration Number",default=0, groups='hr.group_hr_user',required=True)
    sync_first_contract_date = fields.Date("Sync First Contract Date", compute='compute_first_contract_date', store=True, groups='hr.group_hr_user')
    payroll_account_number = fields.Char('Payroll Account Number', groups="hr.group_hr_user", related= "company_id.payroll_account_number")
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True, required=True)
    territory_of_employment = fields.Many2one("res.country.state", groups="hr.group_hr_user", default=lambda self: self.env.company.state_id)
    # ========================================== YTD Information ===================================
    ytd_cpp_erp = fields.Float("Year To Date CPP Contribution in ERP")
    ytd_previous_cpp = fields.Float("Previous CPP",tracking=True,default=0)
    ytd_cpp = fields.Float("Year To Date CPP",default=0,store=True, groups="hr.group_hr_user")

    #CPP2
    ytd_cpp2_erp = fields.Float("Year To Date CPP2 Contribution in ERP")
    ytd_previous_cpp2 = fields.Float("Previous CPP2", tracking=True, default=0)
    ytd_cpp2 = fields.Float("Year To Date CPP2", default=0, store=True, groups="hr.group_hr_user")
    # EI
    ytd_ei_erp = fields.Float("Year To Date EI Contribution in ERP")
    ytd_previous_ei = fields.Float("Previous EI", tracking=True, default=0)
    ytd_ei = fields.Float("Year To Date EI", default=0, store=True, groups="hr.group_hr_user")

    # EI Employer
    ytd_ei_employer_erp = fields.Float("Year To Date Employer EI  Contribution in ERP")
    ytd_previous_ei_employer = fields.Float("Previous Employer EI ", tracking=True, default=0)
    ytd_ei_employer = fields.Float("Year To Date Employer EI", default=0, store=True, groups="hr.group_hr_user")

    #PIYTD
    ytd_pi = fields.Float("Year To Date PI/IE", default=0, store=True,groups="hr.group_hr_user")
    ytd_pi_erp = fields.Float("Year To Date PI/IE ERP", default=0, store=True)
    ytd_previous_pi = fields.Float("Previous Year To Date PI/IE", default=0, store=True)

    # YTDIrregularPaymentFedTaxAmount
    year_to_date_irregular_payment = fields.Float("Year To Date Irregular Payment", default=0, store=True)
    ytd_previous_irre_payment = fields.Float("Previous Year To Date Irregular Payment", default=0, store=True)
    ytd_previous_irre_payment_erp = fields.Float("Year To Date Irregular Payment ERP", default=0)

    #========================================== need to remove this fields=====================================
    ytd_irre_fed_tax = fields.Float("Year To Date Irregular Payment Fed Tax", default=0, store=True, compute='_compute_ytd_irre_fed_tax',groups="hr.group_hr_user")
    ytd_irre_fed_tax_erp = fields.Float("Year To Date Irregular Payment Fed Tax ERP", default=0, store=True)
    ytd_previous_irre_fed_tax = fields.Float("Previous Year To Date Irregular Payment Fed Tax", default=0, store=True,compute='compute_ytd_previous_irre_fed_tax')
    ytd_irre_prov_tax = fields.Float("Year To Date Irregular Payment Prov Tax", default=0, store=True,
                                    compute='_compute_ytd_irre_prov_tax',groups="hr.group_hr_user")
    ytd_irre_prov_tax_erp = fields.Float("Year To Date Irregular Payment Prov Tax ERP", default=0, store=True)
    ytd_previous_irre_prov_tax = fields.Float("Previous Year To Date Irregular Payment Prov Tax", default=0, store=True, compute='compute_ytd_previous_irre_prov_tax')
    ytd_previous_irre_prov_amount = fields.Float("Previous Year To Date Irregular Amount", default=0, store=True)
    last_paycycle_gross = fields.Float("Last Paycycle Wage",help="Last paycycle wage for which the previous bonus was given ",  default=0, store=True)
    #============================================================================================================

    #==================================T4 INFORMATION======================================
    employee_cpp_qpp_xmpt_cd = fields.Selection(selection=CODE,default="0",
                                                string="Canada Pension Plan Or Quebec Pension Plan Exempt Code", help="- T4 slip, box 28\
       - 0 if no exemption applies or if the employee is exempt for a portion of the period\
       - 1 if the employee has been exempt from CPP or QPP for the entire period of employment due to age, nature of payment, etc.")
    employee_ei_xmpt_cd = fields.Selection(selection=CODE,default='0', string="Employment Insurance Exempt Code", help="- T4 slip, box 28\
       - 0 if no exemption applies or if the employee is exempt for a portion of the period\
       - 1 if the employee has been exempt from EI premiums for the entire period of employment due to age, nature of employment, etc.")
    empr_dntl_ben_rpt_cd = fields.Selection(
        selection=[('1', 'Not eligible to access any dental care insurance, or coverage of dental service of any kind'),
                   ('2', 'Payee only'),
                   ('3', 'Payee, spouse and dependent children'),
                   ('4', 'Payee and their spouse'),
                   ('5', 'Payee and their dependent children'), ], string="Employer-offered Dental Benefits", help="""- Required, 1 numeric
           - T4 slip, box 45
           For 2023 and subsequent calendar years, it is mandatory to indicate whether the employee or any of their family members were eligible or not, on December 31 of that year, to access any dental care insurance, or coverage of dental services of any kind, that you offered.

           1 - Not eligible to access any dental care insurance, or coverage of dental service of any kind
           2 - Payee only
           3 - Payee, spouse and dependent children
           4 - Payee and their spouse
           5 - Payee and their dependent children""", default='1')
    employee_empt_cd = fields.Selection(selection=EMPLOYMENT_CODE, default="11",string="Employment Code", help="- T4 slip, box 29\
        - Do not complete Box 14 - Employment income, if you are using employment codes 11, 12, 13, or 17.\
        11 - Placement or employment agency workers\
        12 - Drivers of taxis or other passenger-carrying vehicles\
        13 - Barbers or hairdressers\
        14 - Withdrawal from a prescribed salary deferral arrangement plan\
        15 - Seasonal Agricultural Workers Program\
        16 - Detached employee - Social security agreement.\
        Note: When CPP is paid by the employer on behalf of detached employees under employment code 16, box 14 is left blank if no other type of income is reported. Boxes 16 and 26 are completed with the appropriate amounts and boxes 18 and 24 are left blank.\
        17 - Fishers - Self-employed",)

    employee_prov_pip_xmpt_cd = fields.Selection(selection=CODE,  string="PPIP Exempt Code", help="- T4 slip, box 28\
    - 0 if no exemption applies\
    - 1 if the employee has been exempt", default='0')

    @api.depends("ytd_previous_irre_payment", "ytd_previous_irre_payment_erp")
    def _compute_ytd_irre_payment(self):
        for rec in self:
            rec.year_to_date_irregular_payment = rec.ytd_previous_irre_payment + rec.ytd_previous_irre_payment_erp

    @api.depends("ytd_irre_prov_tax_erp", "ytd_previous_irre_prov_tax")
    def _compute_ytd_irre_prov_tax(self):
        for rec in self:
            rec.ytd_irre_prov_tax = rec.ytd_irre_prov_tax_erp + rec.ytd_previous_irre_prov_tax

    @api.depends("ytd_irre_fed_tax_erp", "ytd_previous_irre_fed_tax")
    def _compute_ytd_irre_fed_tax(self):
        for rec in self:
            rec.ytd_irre_fed_tax = rec.ytd_irre_fed_tax_erp + rec.ytd_previous_irre_fed_tax

    @api.depends("ytd_pi_erp", "ytd_previous_pi")
    def _compute_ytd_pi(self):
        for rec in self:
            rec.ytd_pi = rec.ytd_pi_erp + rec.ytd_previous_pi

    @api.depends("ytd_cpp_erp","ytd_previous_cpp")
    def _compute_ytd_cpp(self):
        for rec in self:
            rec.ytd_cpp = rec.ytd_cpp_erp + rec.ytd_previous_cpp

    @api.depends("ytd_cpp2_erp", "ytd_previous_cpp2")
    def _compute_ytd_cpp2(self):
        for rec in self:
            rec.ytd_cpp2 = rec.ytd_cpp2_erp + rec.ytd_previous_cpp2

    @api.depends("ytd_ei_erp", "ytd_previous_ei")
    def _compute_ytd_ei(self):
        for rec in self:
            rec.ytd_ei = rec.ytd_ei_erp + rec.ytd_previous_ei

    @api.depends("ytd_ei_employer_erp", "ytd_previous_ei_employer")
    def _compute_ytd_ei_employer(self):
        for rec in self:
            rec.ytd_ei_employer = rec.ytd_ei_employer_erp + rec.ytd_previous_ei_employer


    def _get_ytd_payslip_line_ids(self, year):
        """
            This is helper function to get YTD paid payslips compute line ids
        """
        # payslip_ytd = self.slip_ids.filtered(lambda x: x.state == 'paid' and (x.paid_date.year if x.paid_date else x.write_date.year) == int(self.contract_id.deductions.slab_year or 0))
        payslip_ytd = self.slip_ids.filtered(lambda x: x.state == 'paid' and x.date_to.year == int(year))
        return payslip_ytd.line_ids

    def _update_ytd_cpp_pi_ei(self,payslip_ytd,req_type, year, action=None):
        line_obj = self.payroll_line_ids.filtered(lambda x: x.year == str(year))
        if req_type in ['CPP', "CPP2","EI","EI_EMPLOYER"]:
            ytd_total_amount = sum(
                payslip_ytd.filtered(lambda x: x.code == req_type).mapped("total"))

            # todo need to test the task "is_vacation_pay_carry_over"
            if self.is_vacation_pay_carry_over:
                prev_line_obj = self.payroll_line_ids.filtered(lambda x: x.year == str(year - 1))
                if prev_line_obj and not action == 'cancel':
                    if req_type == 'CPP':
                        ytd_total_amount += prev_line_obj.ytd_cpp_erp
                    elif req_type == 'CPP2':
                        ytd_total_amount += prev_line_obj.ytd_cpp2_erp
                    elif req_type == 'EI':
                        ytd_total_amount += prev_line_obj.ytd_ei_erp
                    elif req_type == 'EI_EMPLOYER':
                        ytd_total_amount += prev_line_obj.ytd_ei_employer_erp
            if not line_obj and not action == 'cancel':
                self.env["hr.employee.ytd.payroll.information"].create(
                    {
                        "head_id": self.id,
                        "year": str(year),
                        "ytd_cpp_erp": ytd_total_amount if req_type == 'CPP' else 0,
                        "ytd_cpp2_erp": ytd_total_amount if req_type == 'CPP2' else 0,
                        "ytd_ei_erp": ytd_total_amount if req_type == 'EI' else 0,
                        "ytd_ei_employer_erp": ytd_total_amount if req_type == 'EI_EMPLOYER' else 0,
                        "ytd_pi_erp": prev_line_obj.ytd_pi_erp if self.is_vacation_pay_carry_over and prev_line_obj else 0,
                    }
                )

            else:
                line_obj.ytd_cpp_erp = ytd_total_amount if req_type == 'CPP' else line_obj.ytd_cpp_erp
                line_obj.ytd_cpp2_erp = ytd_total_amount if req_type == 'CPP2' else line_obj.ytd_cpp2_erp
                line_obj.ytd_ei_erp = ytd_total_amount if req_type == 'EI' else line_obj.ytd_ei_erp
                line_obj.ytd_ei_employer_erp = ytd_total_amount if req_type == 'EI_EMPLOYER' else line_obj.ytd_ei_employer_erp

            # if req_type == 'CPP':
            #     self.ytd_cpp_erp = ytd_total_amount
            # elif req_type == 'CPP2':
            #     self.ytd_cpp2_erp = ytd_total_amount
            # elif req_type == 'EI':
            #     self.ytd_ei_erp = ytd_total_amount
            # elif req_type == 'EI_EMPLOYER':
            #     self.ytd_ei_employer_erp = ytd_total_amount

        elif req_type in ['PI']:
            ytd_total_amount = sum(payslip_ytd.filtered(lambda x: x.category_id.code in ["GROSS", "ADD_ALLOWANCE", "ALW"]).mapped("total"))
            prev_line_obj = self.payroll_line_ids.filtered(lambda x: x.year == str(year - 1))
            if self.is_vacation_pay_carry_over and prev_line_obj and not action == 'cancel':
                ytd_total_amount += prev_line_obj.ytd_pi_erp
            # self.ytd_pi_erp = ytd_total_amount
            if not line_obj and not action == 'cancel':
                self.env["hr.employee.ytd.payroll.information"].create(
                    {
                        "head_id": self.id,
                        "year": str(year),
                        "ytd_pi_erp": ytd_total_amount,
                    }
                )
            else:
                line_obj.ytd_pi_erp = ytd_total_amount
        
    def update_ytd_erp(self):
        for rec in self:
            year = self.env.context['year']
            action = self.env.context['action']
            line_obj = self.payroll_line_ids.filtered(lambda x: x.year == str(year))
            is_new_row = False if not line_obj else True
            
            payslip_ytd = rec._get_ytd_payslip_line_ids(year)
            if self.env.context['type'] == "ALL":
                for i in ["CPP", "CPP2", "PI","EI","EI_EMPLOYER"]:
                    rec._update_ytd_cpp_pi_ei(payslip_ytd,i,year, action)
            else:
                rec._update_ytd_cpp_pi_ei(payslip_ytd,rec.env.context.get('type'),year, action)

            rec.update_ytd_irregular_payments_tax(year, line_obj, action, is_new_row)

    # def _update_ytd_irregular_payments_tax(self,payslip_ytd,req_type):
    #         ytd_total_amount = payslip_ytd.filtered(lambda x: x.category_id.code in ["ADD_ALLOWANCE"])
    #         self.ytd_pi_erp = ytd_total_amount

    def update_ytd_irregular_payments_tax(self, year, line_obj, action=None, is_new_row=False):
        for rec in self:
            if not line_obj:
                line_obj = self.payroll_line_ids.filtered(lambda x: x.year == str(year))

            payslip_ytd_ids = rec.slip_ids.filtered(lambda x: x.state == 'paid' and (x.date_to.year if x.date_to else x.write_date.year) == int(year))
            irre_amount = sum(payslip_ytd_ids.mapped("irre_amount"))

            # Update irregular payments for the current year
            if line_obj:
                line_obj.ytd_previous_irre_payment_erp = irre_amount
                line_obj.ytd_previous_irre_payment = line_obj.ytd_previous_irre_payment if payslip_ytd_ids else 0
                line_obj.year_to_date_irregular_payment = line_obj.ytd_previous_irre_payment_erp + line_obj.ytd_previous_irre_payment

            # If vacation pay carryover is enabled, add the previous year's irregular amounts
            if line_obj and rec.is_vacation_pay_carry_over and not action == 'cancel':
                previous_year_lines = rec.payroll_line_ids.filtered(lambda x: str(x.year) == str(year - 1))
                if previous_year_lines:
                    line_obj.ytd_previous_irre_payment_erp += previous_year_lines.ytd_previous_irre_payment_erp
                    line_obj.ytd_previous_irre_payment = previous_year_lines.ytd_previous_irre_payment if is_new_row else line_obj.ytd_previous_irre_payment_erp
                    line_obj.year_to_date_irregular_payment = line_obj.ytd_previous_irre_payment_erp + line_obj.ytd_previous_irre_payment

    # def update_ytd_irregular_payments_tax(self, year, irre_amount):
    #     for rec in self:
    #         # Filter payroll lines for the current year and previous year
    #         current_year_lines = rec.payroll_line_ids.filtered(lambda x: str(x.year) == str(year))
    # 
    #         # Update irregular payments for the current year
    #         if current_year_lines:
    #             current_year_lines.ytd_previous_irre_payment_erp += irre_amount
    #             current_year_lines.year_to_date_irregular_payment = current_year_lines.ytd_previous_irre_payment_erp + current_year_lines.ytd_previous_irre_payment
    # 
    #         # If vacation pay carryover is enabled, add the previous year's irregular amounts
    #         if rec.is_vacation_pay_carry_over:
    #             previous_year_lines = rec.payroll_line_ids.filtered(lambda x: str(x.year) == str(year - 1))
    #             if previous_year_lines:
    #                 current_year_lines.ytd_previous_irre_payment_erp += previous_year_lines.ytd_previous_irre_payment_erp
    #                 current_year_lines.ytd_previous_irre_payment = previous_year_lines.ytd_previous_irre_payment
    #                 current_year_lines.year_to_date_irregular_payment = current_year_lines.ytd_previous_irre_payment_erp + previous_year_lines.ytd_previous_irre_payment

            # payslip_ytd_tax = self.slip_ids.filtered(
            # lambda x: x.state == 'paid' and (
            #     x.paid_date.year if x.paid_date else x.write_date.year) == int(
            #     self.contract_id.deductions.slab_year or 0))

            # rec.ytd_previous_irre_payment_erp = sum(payslip_ytd_tax.mapped("irre_amount"))
            # rec.ytd_irre_fed_tax_erp = sum(payslip_ytd_tax.mapped("irre_fed_tax"))
            # rec.ytd_irre_prov_tax_erp = sum(payslip_ytd_tax.mapped("irre_prov_tax"))

    @api.depends('ytd_previous_irre_prov_amount', 'last_paycycle_gross')
    def compute_ytd_previous_irre_fed_tax(self):
        for rec in self:
            is_pay_cycle = rec.contract_id.salary_pay_cycle.pay_cycle
            paycycle_gross = rec.last_paycycle_gross
            # paycycle_gross = self.contract_id.paycyle_wage - categories['PRE_TAX_DEDUCTION'] FIX
            if is_pay_cycle:
                pay_cycle = int(is_pay_cycle)
                claim_code = rec.contract_id.federal_claim_code_from_td1
                year = rec.contract_id.deductions.slab_year
                total_gross_with_irr = (rec.ytd_previous_irre_prov_amount / pay_cycle) + paycycle_gross

                tax_amount_gross_without_irr = rec.env['fed.tax'].get_tax_amount(paycycle_gross, claim_code, year,
                                                                                   pay_cycle)
                tax_amount_gross_with_irr = rec.env['fed.tax'].get_tax_amount(total_gross_with_irr, claim_code, year,
                                                                                pay_cycle)

                irr_pay_tax = tax_amount_gross_with_irr - tax_amount_gross_without_irr
                rec.ytd_previous_irre_fed_tax = irr_pay_tax * pay_cycle

    @api.depends('ytd_previous_irre_prov_amount','last_paycycle_gross')
    def compute_ytd_previous_irre_prov_tax(self):
        for rec in self:
            is_pay_cycle = rec.contract_id.salary_pay_cycle.pay_cycle
            paycycle_gross = rec.last_paycycle_gross
            # paycycle_gross = self.contract_id.paycyle_wage - categories['PRE_TAX_DEDUCTION'] FIX
            if is_pay_cycle:
                pay_cycle = int(is_pay_cycle)
                claim_code = rec.contract_id.federal_claim_code_from_td1
                year = rec.contract_id.deductions.slab_year
                total_gross_with_irr = (rec.ytd_previous_irre_prov_amount / pay_cycle) + paycycle_gross

                tax_amount_gross_without_irr = rec.env['prov.tax'].get_tax_amount(paycycle_gross, claim_code, year,
                                                                                     pay_cycle)
                tax_amount_gross_with_irr = rec.env['prov.tax'].get_tax_amount(total_gross_with_irr, claim_code, year,
                                                                                  pay_cycle)

                irr_pay_tax = tax_amount_gross_with_irr - tax_amount_gross_without_irr
                rec.ytd_previous_irre_prov_tax = irr_pay_tax * pay_cycle

    @api.onchange('is_portal_user')
    def _onchage_is_portal_user(self):
        for x in self:
            x.portal_user_id = None

    @api.onchange('portal_user_id')
    def _onchage_portal_user_id(self):
        for x in self:
            if x.portal_user_id:
                existing_user = self.search([
                    ('portal_user_id', '=', x.portal_user_id.id),('id', '!=', x._origin.id)
                ], limit=1)
                if existing_user:
                    raise UserError("This User is already mapped with another employee!")


    @api.depends('first_contract_date')
    def compute_first_contract_date(self):
        for rec in self:
            if rec.first_contract_date:
                rec.sync_first_contract_date = rec.first_contract_date

    @api.model
    def action_statement_remuneration_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'T4 Batch Generation',
            'res_model': 'statement.remuneration.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def action_update_batch_payroll_info(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch Update Payroll Info',
            'res_model': 'payroll.update.wizard',
            'view_mode': 'form',
            'target': 'new',
        }


class HrEmployeeYTDPayrollInformation(models.Model):
    _name = 'hr.employee.ytd.payroll.information'
    _description = 'Hr Employee YTD Payroll Information'

    head_id = fields.Many2one('hr.employee')
    contract_id = fields.Many2one('hr.contract',related='head_id.contract_id', store=True)
    last_paycycle_gross = fields.Float(related='head_id.last_paycycle_gross', store=True)
    ytd_previous_irre_prov_amount = fields.Float(related='head_id.ytd_previous_irre_prov_amount', store=True)
    year = fields.Selection(
        year_selection,
        string="Year",
        default=lambda self: str(datetime.now().year)
    )
    ytd_previous_irre_fed_tax = fields.Float("Previous Year To Date Irregular Payment Fed Tax", default=0, store=True,
                                             compute='compute_ytd_previous_irre_fed_tax')

    ytd_cpp_erp = fields.Float("Year To Date CPP Contribution in ERP")
    ytd_previous_cpp = fields.Float("Previous CPP", tracking=True, default=0)
    ytd_cpp = fields.Float("Year To Date CPP", default=0, store=True, compute='_compute_ytd_cpp',
                           groups="hr.group_hr_user")

    # CPP2
    ytd_cpp2_erp = fields.Float("Year To Date CPP2 Contribution in ERP")
    ytd_previous_cpp2 = fields.Float("Previous CPP2", tracking=True, default=0)
    ytd_cpp2 = fields.Float("Year To Date CPP2", default=0, store=True, compute='_compute_ytd_cpp2',
                            groups="hr.group_hr_user")
    # EI
    ytd_ei_erp = fields.Float("Year To Date EI Contribution in ERP")
    ytd_previous_ei = fields.Float("Previous EI", tracking=True, default=0)
    ytd_ei = fields.Float("Year To Date EI", default=0, store=True, compute='_compute_ytd_ei',
                          groups="hr.group_hr_user")

    # EI Employer
    ytd_ei_employer_erp = fields.Float("Year To Date Employer EI Contribution in ERP")
    ytd_previous_ei_employer = fields.Float("Previous Employer EI ", tracking=True, default=0)
    ytd_ei_employer = fields.Float("Year To Date Employer EI", default=0, store=True,
                                   compute='_compute_ytd_ei_employer', groups="hr.group_hr_user")

    # PIYTD
    ytd_pi = fields.Float("Year To Date PI/IE", default=0, store=True, compute='_compute_ytd_pi',
                          groups="hr.group_hr_user")
    ytd_pi_erp = fields.Float("Year To Date PI/IE ERP", default=0, store=True)
    ytd_previous_pi = fields.Float("Previous Year To Date PI/IE", default=0, store=True)

    # YTDIrregularPaymentFedTaxAmount
    year_to_date_irregular_payment = fields.Float("Year To Date Irregular Payment", default=0, store=True,
                                                  compute="_compute_ytd_irre_payment")
    ytd_previous_irre_payment = fields.Float("Previous Year To Date Irregular Payment", default=0, store=True,
                                             )
    ytd_previous_irre_payment_erp = fields.Float("Year To Date Irregular Payment ERP", default=0, store=True,
                                                 compute='compute_ytd_previous_irre_fed_tax')

    # _sql_constraints = [
    #     ('name_year_unique', 'unique (head_id, year)', 'The combination code/payment type already exists!'),
    # ]

    @api.constrains('year')
    def _check_year(self):
        self.ensure_one()
        records_count = self.search_count([('year', '=', self.year),('head_id', '=', self.head_id.id)])
        if records_count > 1:
            raise UserError(_("Duplicate Error: Year already exists."))

    @api.depends("ytd_cpp_erp","ytd_previous_cpp")
    def _compute_ytd_cpp(self):
        for rec in self:
            rec.ytd_cpp = rec.ytd_cpp_erp + rec.ytd_previous_cpp

    @api.depends("ytd_cpp2_erp", "ytd_previous_cpp2")
    def _compute_ytd_cpp2(self):
        for rec in self:
            rec.ytd_cpp2 = rec.ytd_cpp2_erp + rec.ytd_previous_cpp2

    @api.depends("ytd_ei_erp", "ytd_previous_ei")
    def _compute_ytd_ei(self):
        for rec in self:
            rec.ytd_ei = rec.ytd_ei_erp + rec.ytd_previous_ei

    @api.depends("ytd_ei_employer_erp", "ytd_previous_ei_employer")
    def _compute_ytd_ei_employer(self):
        for rec in self:
            rec.ytd_ei_employer = rec.ytd_ei_employer_erp + rec.ytd_previous_ei_employer

    @api.depends("ytd_pi_erp", "ytd_previous_pi")
    def _compute_ytd_pi(self):
        for rec in self:
            rec.ytd_pi = rec.ytd_pi_erp + rec.ytd_previous_pi

    @api.depends("ytd_previous_irre_payment", "ytd_previous_irre_payment_erp")
    def _compute_ytd_irre_payment(self):
        for rec in self:
            rec.year_to_date_irregular_payment = rec.ytd_previous_irre_payment + rec.ytd_previous_irre_payment_erp

    @api.depends('ytd_previous_irre_prov_amount', 'last_paycycle_gross')
    def compute_ytd_previous_irre_fed_tax(self):
        for rec in self:
            is_pay_cycle = rec.contract_id.salary_pay_cycle.pay_cycle
            paycycle_gross = rec.last_paycycle_gross
            # paycycle_gross = self.contract_id.paycyle_wage - categories['PRE_TAX_DEDUCTION'] FIX
            if is_pay_cycle:
                pay_cycle = int(is_pay_cycle)
                claim_code = rec.contract_id.federal_claim_code_from_td1
                year = rec.contract_id.deductions.slab_year
                total_gross_with_irr = (rec.ytd_previous_irre_prov_amount / pay_cycle) + paycycle_gross

                tax_amount_gross_without_irr = rec.env['fed.tax'].get_tax_amount(paycycle_gross, claim_code, year,
                                                                                   pay_cycle)
                tax_amount_gross_with_irr = rec.env['fed.tax'].get_tax_amount(total_gross_with_irr, claim_code, year,
                                                                                pay_cycle)

                irr_pay_tax = tax_amount_gross_with_irr - tax_amount_gross_without_irr
                rec.ytd_previous_irre_fed_tax = irr_pay_tax * pay_cycle

    def update_ytd_erp(self):
        for rec in self:
            year = self.env.context['year'] if 'year' in self.env.context else self.year
            payslip_ytd = rec.head_id._get_ytd_payslip_line_ids(int(year))
            if self.env.context['type'] == "ALL":
                for i in ["CPP", "CPP2", "PI","EI","EI_EMPLOYER"]:
                    rec.head_id._update_ytd_cpp_pi_ei(payslip_ytd,i,int(year))
            else:
                rec.head_id._update_ytd_cpp_pi_ei(payslip_ytd,rec.env.context.get('type'),int(year))

    # def _update_ytd_irregular_payments_tax(self,payslip_ytd,req_type):
    #         ytd_total_amount = payslip_ytd.filtered(lambda x: x.category_id.code in ["ADD_ALLOWANCE"])
    #         self.ytd_pi_erp = ytd_total_amount

    def update_ytd_irregular_payments_tax(self):
        for rec in self:
            rec.head_id.update_ytd_irregular_payments_tax(int(self.year), rec)

            # payslip_ytd_tax = self.head_id.slip_ids.filtered(
            # lambda x: x.state == 'paid' and (
            #     x.date_to.year if x.date_to else x.write_date.year) == int(self.year))
            # rec.ytd_previous_irre_payment_erp = sum(payslip_ytd_tax.mapped("irre_amount"))

    # def update_ytd_irregular_payments_tax(self):
    #     for rec in self:
    #         payslip_ytd_tax = self.head_id.slip_ids.filtered(
    #         lambda x: x.state == 'paid' and (
    #             x.date_to.year if x.date_to else x.write_date.year) == int(
    #             self.contract_id.deductions.slab_year or 0) and (x.irre_fed_tax > 0.0 or x.irre_prov_tax > 0.0 ))
    #         rec.ytd_previous_irre_payment_erp = sum(payslip_ytd_tax.mapped("irre_amount"))
