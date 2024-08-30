from odoo import models, api, fields, _


class InhertitedHrEmployee(models.Model):
    _inherit = 'hr.employee'

    _sql_constraints = [
        ('identification_id_len', 'CHECK (LENGTH(identification_id) = 9)', ('Social Insurance Number Must be of 9 digits.')),
        # ('registration_number_verification', 'CHECK (registration_number SIMILAR TO ^[178][0-9]{8}(RP|RW)[0-9]{4}$)', ('Payroll Account Number Must Match patterns.')),
    ]

    employee_prpp_dpsp_rgst_nbr = fields.Integer(string="RPP or DPSP Registration Number Registration Number",deafult=0, groups='hr.group_hr_user',required=True)
    sync_first_contract_date = fields.Date("First Contract Date", compute='compute_first_contract_date', store=True, groups='hr.group_hr_user')
    payroll_account_number = fields.Char('Payroll Account Number', groups="hr.group_hr_user", related= "company_id.payroll_account_number")
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True, required=True)

    # ========================================== YTD Information ===================================
    ytd_cpp_erp = fields.Float("Year To Date CPP contribution in ERP")
    ytd_previous_cpp = fields.Float("Previous CPP",tracking=True,default=0)
    ytd_cpp = fields.Float("Year To Date CPP",default=0,store=True,compute='_compute_ytd_cpp')

    #CPP2
    ytd_cpp2_erp = fields.Float("Year To Date CPP2 contribution in ERP")
    ytd_previous_cpp2 = fields.Float("Previous CPP2", tracking=True, default=0)
    ytd_cpp2 = fields.Float("Year To Date CPP2", default=0, store=True, compute='_compute_ytd_cpp2')
    # EI
    ytd_ei_erp = fields.Float("Year To Date EI contribution in ERP")
    ytd_previous_ei = fields.Float("Previous EI", tracking=True, default=0)
    ytd_ei = fields.Float("Year To Date EI", default=0, store=True, compute='_compute_ytd_ei')

    # EI Employer
    ytd_ei_employer_erp = fields.Float("Year To Date Employer EI  contribution in ERP")
    ytd_previous_ei_employer = fields.Float("Previous Employer EI ", tracking=True, default=0)
    ytd_ei_employer = fields.Float("Year To Date Employer EI", default=0, store=True, compute='_compute_ytd_ei_employer')

    #PIYTD
    ytd_pi = fields.Float("Year To Date PI/IE", default=0, store=True, compute='_compute_ytd_pi')
    ytd_pi_erp = fields.Float("Year To Date PI/IE ERP", default=0, store=True)
    ytd_previous_pi = fields.Float("Previous Year To Date PI/IE", default=0, store=True)

    # YTDIrregularPaymentFedTax
    ytd_irre_fed_tax = fields.Float("Year To Date Irregular Payment Fed Tax", default=0, store=True, compute='_compute_ytd_irre_fed_tax')
    ytd_irre_fed_tax_erp = fields.Float("Year To Date Irregular Payment Fed Tax ERP", default=0, store=True)
    ytd_previous_irre_fed_tax = fields.Float("Previous Year To Date Irregular Payment Fed Tax", default=0, store=True)

    # YTDIrregularPaymentProvTax
    ytd_irre_prov_tax = fields.Float("Year To Date Irregular Payment Prov Tax", default=0, store=True,
                                    compute='_compute_ytd_irre_prov_tax')
    ytd_irre_prov_tax_erp = fields.Float("Year To Date Irregular Payment Prov Tax ERP", default=0, store=True)
    ytd_previous_irre_prov_tax = fields.Float("Previous Year To Date Irregular Payment Prov Tax", default=0, store=True)

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


    def _get_ytd_payslip_line_ids(self):
        """
            This is helper function to get YTD paid payslips compute line ids
        """
        payslip_ytd = self.slip_ids.filtered(
            lambda x: x.state == 'paid' and (
                x.paid_date.year if x.paid_date else x.write_date.year) == int(
                self.contract_id.deductions.slab_year or 0))

        return payslip_ytd.line_ids

    def _update_ytd_cpp_pi_ei(self,payslip_ytd,req_type):
        if req_type in ['CPP', "CPP2","EI","EI_EMPLOYER"]:
            ytd_total_amount = sum(
                payslip_ytd.filtered(lambda x: x.code == req_type).mapped("total"))
            if req_type == 'CPP':
                self.ytd_cpp_erp = ytd_total_amount
            elif req_type == 'CPP2':
                self.ytd_cpp2_erp = ytd_total_amount
            elif req_type == 'EI':
                self.ytd_ei_erp = ytd_total_amount
            elif req_type == 'EI_EMPLOYER':
                self.ytd_ei_employer_erp = ytd_total_amount
        elif req_type in ['PI']:
            ytd_total_amount = sum(
                payslip_ytd.filtered(lambda x: x.category_id.code in ["GROSS", "ADD_ALLOWANCE", "ALW"]).mapped("total"))
            self.ytd_pi_erp = ytd_total_amount

    def update_ytd_erp(self):
        for rec in self:
            payslip_ytd = rec._get_ytd_payslip_line_ids()
            if self.env.context['type'] == "ALL":
                for i in ["CPP", "CPP2", "PI","EI","EI_EMPLOYER"]:
                    rec._update_ytd_cpp_pi_ei(payslip_ytd,i)
            else:
                rec._update_ytd_cpp_pi_ei(payslip_ytd,rec.env.context.get('type'))



    def _update_ytd_irregular_payments_tax(self,payslip_ytd,req_type):

            ytd_total_amount = payslip_ytd.filtered(lambda x: x.category_id.code in ["ADD_ALLOWANCE"])
            self.ytd_pi_erp = ytd_total_amount

    def update_ytd_irregular_payments_tax(self):
        for rec in self:
            payslip_ytd_tax = self.slip_ids.filtered(
            lambda x: x.state == 'paid' and (
                x.paid_date.year if x.paid_date else x.write_date.year) == int(
                self.contract_id.deductions.slab_year or 0) and (x.irre_fed_tax > 0.0 or x.irre_prov_tax > 0.0 ))
            rec.ytd_irre_fed_tax_erp = sum(payslip_ytd_tax.mapped("irre_fed_tax"))
            rec.ytd_irre_prov_tax_erp = sum(payslip_ytd_tax.mapped("irre_prov_tax"))





    @api.depends('first_contract_date')
    def compute_first_contract_date(self):
        for rec in self:
            if rec.first_contract_date:
                rec.sync_first_contract_date = rec.first_contract_date
