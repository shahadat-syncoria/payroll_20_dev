# -*- coding: utf-8 -*-
import os

from lxml import etree

from odoo import models, fields, api, _
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError

from odoo.modules import get_resource_from_path
from odoo.tools.misc import file_path

import datetime

from pypdf import PdfReader, PdfWriter
from ..helper.helper_functions import year_selection

CODE = [
    ('0', '0'),
    ('1', '1'),
]
EMPLOYMENT_CODE = [
    ('11', "Placement or employment agency workers"),
    ('12', "Drivers of taxis or other passenger-carrying vehicles"),
    ('13', "Barbers or hairdressers"),
    ('14', "Withdrawal from a prescribed salary deferral arrangement plan"),
    ('15', "Seasonal Agricultural Workers Program"),
    ('16', "Detached employee - Social security agreement."),
    ('17', "Fishers - Self-employed"),
]
REPORT_TYPE_CODE = [
    ('O', 'originals'),
    ('A', 'Amendments'),
    ('C', 'Cancel'),
]
PROVINCE_CODE = [
    ('AB', 'Alberta'),
    ('BC', 'British Columbia'),
    ('MB', 'Manitoba'),
    ('NB', 'New Brunswick'),
    ('NL', 'Newfoundland and Labrador'),
    ('NS', 'Nova Scotia'),
    ('NT', 'Northwest Territories'),
    ('NU', 'Nunavut'),
    ('ON', 'Ontario'),
    ('PE', 'Prince Edward Island'),
    ('QC', 'Quebec'),
    ('SK', 'Saskatchewan'),
    ('YT', 'Yukon Territories'),
    ('US', 'United States'),
    ('ZZ', 'Other')
]


class StatementOfRemuneration(models.Model):
    _name = 'statement.remuneration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = ' Statement of Remuneration Paid(T4)'
    _rec_name = 'name'


    xml_content = fields.Text(string='XML Content')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    employer_id = fields.Many2one('res.partner', related='company_id.partner_id')

    year = fields.Selection(
        year_selection,
        string="Year",
        default='2023'
    )
    # ============ Employee Information ================
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee ',
        required=True, store=True)
    name = fields.Char("Name", related='employee_id.name', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
        tracking=True, help='Status of the T4 form', default='draft')

    # employee_contract = fields.Many2one(
    #     comodel_name='hr.version',
    #     string='Employee Contract',
    #     required=True,
    #     # domain=lambda self: self._domain_contract_ids(),
    #     # domain=[('employee_id','=' ,employee_id)],
    # )
    employee_contract = fields.Many2one('hr.version', string="Employee Contract")

    # ======================= Previous =============================
    #     employment_income = fields.Float("Employment Income")
    #     employment_income_tax_deducted = fields.Float("Income Tax Deducted")
    #     employment_province = fields.Char("Province of Employment",related='employee_id.address_id.state_id.code')
    #     employee_cpp_contribution = fields.Float("Employee's CPP Contributions")
    #     employee_ei_insu_earning = fields.Float("EI insurable Earning")
    #     employment_code = fields.Char("Employment Code")
    #     employee_qpp_contribution = fields.Float("Employee QPP Contributions")
    #     employee_c_q_pp_contribution = fields.Float("Employee CPP/QPP Contributions")
    #     employee_ei_premiums = fields.Float("Employee's EI premiums")
    #     employee_union_dues = fields.Float("Union Dues")
    #     employee_rpp_contribution = fields.Float("Employee's RPP Contributions")
    #     employee_charitable_donation = fields.Float("Employee's Charitable Donations")
    #     employee_pension_adjustment = fields.Float("Employee's Pension Adjustment")
    #     employee_rpp_dpsp_reg_num = fields.Float("RPP Or DPSP Registration Number")
    #     employee_ppip_premiums = fields.Float("Employee's PPIP Premiums")
    #     employee_ppip_insu_earning = fields.Float("Employee's PPIP Insurable Earning")
    #
    #     other_amount = fields.Float("Amount")
    #     autres_amount = fields.Float("Autres Amount")
    #
    #
    # #     employee_snm = fields.Char("Employee surname",size=20,help="- first 20 letters of the employee's surname\
    # # - omit titles such as Mr., Mrs., etc.\
    # # - do not include first name or initials")
    #
    #     employee_cntry_cd = fields.Char("Employee country code",max_size=3,help="""- 3 alpha
    # - country in which the employee is located
    # - use the alphabetic country codes as outlined in the International Standard (ISO) 3166 Codes for the Representation of Names of Countries.
    # - always use CAN for Canada, and USA for the United States of America.""")

    # =====================================================

    # ===============================  Employee Information =======================================
    employee_snm = fields.Char("Employee Surname", size=20, help="- first 20 letters of the employee's surname\
    - omit titles such as Mr., Mrs., etc.\
    - do not include first name or initials")

    employee_gvn_nm = fields.Char("Employee First Name", size=12,
                                  help="-first 12 letters of the employee's first given name")

    employee_init = fields.Char(" Employee Initial", size=1, help="- initial of the employee's second given name")
    employee_addr_l1_txt = fields.Char("Employee Address - line 1", size=30,
                                       help="- first line of the employee's address")
    employee_addr_l2_txt = fields.Char("Employee Address - line 2", size=30,
                                       help="- second line of the employee's address")
    employee_cty_nm = fields.Char("Employee City", size=28, help="- city in which the employee is located.")
    employee_prov_cd = fields.Char("Employee Province Or Territory code", size=2, help="- Canadian province or territory in which the employee is located or the state in the USA where the employee is located\
    - use the abbreviations listed in the T619 - Electronic transmittal under section: Transmitter province or territory code\
    - when the employee's country code is neither CAN nor USA, enter ZZ in this field")
    employee_cntry_cd = fields.Char("Employee Country Code", size=3, help="- country in which the employee is located\
    - use the alphabetic country codes as outlined in the International Standard (ISO) 3166 Codes for the Representation of Names of Countries.\
    -  always use CAN for Canada, and USA for the United States of America.")
    employee_pstl_cd = fields.Char("Employee Postal Code", size=10, help="- employee's Canadian postal code, format: alpha, numeric, alpha, numeric, alpha, numeric, example: A9A9A9\
    - or the employee's USA zip code\
    - or where the employee's country code is neither CAN nor USA, enter the foreign postal code")
    employee_sin = fields.Char("Employee Social Insurance Number (SIN)", help="- T4 slip, box 12\
    - When the employee has failed to provide a SIN, enter zeroes in the entire field.\
    Note: Omission of a valid SIN results in non-registration of contributions to the Canada Pension Plan.")
    employee_empe_nbr = fields.Char("Employee Number", size=20,
                                    help="- for example: region and/or branch payroll and/or department and/or employee number")
    employee_bn = fields.Char(" Employee Payroll Account Number", size=15, help="- T4 slip, box 54\
    - must correspond to the 'Business Number (BN)' on the related T4 Summary record Note: To process a return, the complete BN is required")
    employee_rpp_dpsp_rgst_nbr = fields.Integer("RPP or DPSP Registration Number Registration Number", help="- T4 slip, box 50\
    - enter the registration number for the plan where the employee received the largest pension adjustment amount")
    employee_cpp_qpp_xmpt_cd = fields.Selection(related="employee_id.employee_cpp_qpp_xmpt_cd",
                                                string="Canada Pension Plan or Quebec Pension Plan Exempt Code", help="- T4 slip, box 28\
    - 0 if no exemption applies or if the employee is exempt for a portion of the period\
    - 1 if the employee has been exempt from CPP or QPP for the entire period of employment due to age, nature of payment, etc.")
    employee_ei_xmpt_cd = fields.Selection(related="employee_id.employee_ei_xmpt_cd",string="Employment Insurance Exempt Code", help="- T4 slip, box 28\
    - 0 if no exemption applies or if the employee is exempt for a portion of the period\
    - 1 if the employee has been exempt from EI premiums for the entire period of employment due to age, nature of employment, etc.")
    employee_prov_pip_xmpt_cd = fields.Selection(related="employee_id.employee_prov_pip_xmpt_cd", string="PPIP Exempt Code", help="- T4 slip, box 28\
    - 0 if no exemption applies\
    - 1 if the employee has been exempt")
    employee_empt_cd = fields.Selection(related="employee_id.employee_empt_cd", string="Employment Code", help="- T4 slip, box 29\
    - Do not complete Box 14 - Employment income, if you are using employment codes 11, 12, 13, or 17.\
    11 - Placement or employment agency workers\
    12 - Drivers of taxis or other passenger-carrying vehicles\
    13 - Barbers or hairdressers\
    14 - Withdrawal from a prescribed salary deferral arrangement plan\
    15 - Seasonal Agricultural Workers Program\
    16 - Detached employee - Social security agreement.\
    Note: When CPP is paid by the employer on behalf of detached employees under employment code 16, box 14 is left blank if no other type of income is reported. Boxes 16 and 26 are completed with the appropriate amounts and boxes 18 and 24 are left blank.\
    17 - Fishers - Self-employed")
    employee_rpt_tcd = fields.Selection(selection=REPORT_TYPE_CODE,default="O", string=" Employee Report Type Code", help="- originals = O\
    - amendments = A\
    - cancel = C\
    Note: An amended return cannot contain an original slip")
    employee_empt_prov_cd = fields.Selection(selection=PROVINCE_CODE,
                                             string="Province, Territory Or Country Of Employment Code", help="- T4 slip, box 10\
    - Enter province, territory or country in which the employee was employed\
    - Use the following abbreviations:\
    AB - Alberta\
    BC - British Columbia\
    MB - Manitoba\
    NB - New Brunswick\
    NL - Newfoundland and Labrador\
    NS - Nova Scotia\
    NT - Northwest Territories\
    NU - Nunavut\
    ON - Ontario\
    PE - Prince Edward Island\
    QC - Quebec\
    SK - Saskatchewan\
    YT - Yukon Territories\
    US - United States\
    ZZ - Other")

    # ============================== Employee T4 Amount ========================================
    employee_empt_incamt = fields.Float("Employment Income", help="""-10 numeric
    - T4 slip, box 14
    Note: Do not complete box 14 if you are using employment codes 11, 12, 13, or 17. Refer to box 29 for these codes.""")

    employee_cpp_cntrb_amt = fields.Float("Employee's Canada Pension Plan (CPP) Contributions", help=""""- 6 numeric
    - T4 slip, box 16
    Note: Under no circumstances should amounts for both CPP and QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_cppe_cntrb_amt = fields.Float("Employee's Second Canada Pension Plan (CPP2) Contributions", help=""""- 6 numeric
            - T4 slip, box 16A , (For taxation year 2024 and subsequent)
            Note: Under no circumstances should amounts for both second CPP and second QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_qpp_cntrb_amt = fields.Float("Employee's Quebec Pension Plan (QPP) Contributions", help=""""- 6 numeric
    - T4 slip, box 17
    Note: Under no circumstances should amounts for both CPP and QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_qppe_cntrb_amt = fields.Float("Employee's Second Québec Pension Plan (QPP2) Contributions", help=""""- 6 numeric
            - T4 slip, box 17A, (For taxation year 2024 and subsequent)
            Note: Under no circumstances should amounts for both second CPP and second QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_empe_eip_amt = fields.Float("Employee's Employment Insurance (EI) Premium", help="""" 6 numeric
    - T4 slip, box 18""")

    registered_rpp_cntrb_amt = fields.Float("Registered Pension Plan (RPP) Contributions", help="""" - 7 numeric
    - T4 slip, box 20""")

    income_itx_ddct_amt = fields.Float("Income Tax Deducted", help="""" - 10 numeric
    - T4 slip, box 22""")

    employee_ei_insu_ern_amt = fields.Float("Employment Insurance Insurable Earnings", help="""" - Required 7 numeric
    - T4 slip, box 24
    - enter "0.00" if there are no insurable earnings
    - for exempt employment, enter "0.00" """)

    canada_cpp_qpp_ern_amt = fields.Float("Canada Pension Plan Or Quebec Pension Plan Pensionable Earnings", help="""- Required 9 numeric
    - T4 slip, box 26
    - if there are no pensionable earnings, enter "0.00"
    - for exempt employment, enter "0.00" """)

    union_unn_dues_amt = fields.Float("Union Dues", help="""- 9 numeric
    - T4 slip, box 44 """)

    charitable_chrty_dons_amt = fields.Float("Charitable Donations", help="""- 9 numeric
    - T4 slip, box 46 """)

    pension_padj_amt = fields.Float("Pension Adjustment", help="""- 7 numeric
    - T4 slip, box 52""")

    PPIP_prov_pip_amt = fields.Float("PPIP Premiums", help="""- 6 Numeric
    - T4 Slip, box 55""")

    PPIP_prov_insu_ern_amt = fields.Float("PPIP Insurable Earnings", help="""- 7 Numeric
    - T4 Slip, box 56""")

    # =================================== Other Info ===============================
    # empr_dntl_ben_rpt_cd
    empr_dntl_ben_rpt_cd = fields.Selection(related="employee_id.empr_dntl_ben_rpt_cd",string="Employer-offered Dental Benefits", help="""- Required, 1 numeric
        - T4 slip, box 45
        For 2023 and subsequent calendar years, it is mandatory to indicate whether the employee or any of their family members were eligible or not, on December 31 of that year, to access any dental care insurance, or coverage of dental services of any kind, that you offered.
        
        1 - Not eligible to access any dental care insurance, or coverage of dental service of any kind
        2 - Payee only
        3 - Payee, spouse and dependent children
        4 - Payee and their spouse
        5 - Payee and their dependent children""")
    # hm_brd_lodg_amt
    hm_brd_lodg_amt = fields.Float("Housing, Board And Lodging Amount", help="- Other Income Amount - Code 30")

    # spcl_wrk_site_amt
    spcl_wrk_site_amt = fields.Float("Special Work Site Amount", help="- Other Income Amount - Code 31")

    # prscb_zn_trvl_amt
    prscb_zn_trvl_amt = fields.Float("Travel In A Prescribed Zone Amount", help="- Other Income Amount - Code 32")

    # med_trvl_amt
    med_trvl_amt = fields.Float("Medical Travel Amount", help="- Other Income Amount - Code 33")

    # prsnl_vhcl_amt
    prsnl_vhcl_amt = fields.Float("Personal Use Of Employer Automobile Amount", help="- Other Income Amount - Code 34")

    # rsn_per_km_amt
    rsn_per_km_amt = fields.Float("Total Reasonable Per-Kilometre Allowance Amount",
                                  help="- Other Income amount - Code 35, applies to year 2000 and prior")

    # low_int_loan_amt
    low_int_loan_amt = fields.Float("Interest-free And Low-interest Loan Amount",
                                    help="- Other Income Amount - Code 36")

    # empe_hm_loan_amt
    empe_hm_loan_amt = fields.Float("Employee Home-Relocation Loan Deduction Amount",
                                    help="- Other Income Amount - Code 37")

    # stok_opt_ben_amt
    stok_opt_ben_amt = fields.Float("Stock Option Benefit Amount Before February 28, 2000",
                                    help="- Other Income Amount - Code 97, applies to year 2000 and prior")

    # sob_a00_feb_amt
    sob_a00_feb_amt = fields.Float("Security Options Benefits", help="- Other Income Amount - Code 38")

    # shr_opt_d_ben_amt
    shr_opt_d_ben_amt = fields.Float("Stock Option And Share Deduction 110(1) (d) Amount Before February 28, 2000",
                                     help="- Other Income Amount - Code 98, applies to year 2000 and prior")

    # sod_d_a00_feb_amt
    sod_d_a00_feb_amt = fields.Float("Security Options Deductions 110(1)(d)", help="- Other Income Amount - Code 39")

    # oth_tx_ben_amt
    oth_tx_ben_amt = fields.Float("Other Taxable Allowance And Benefit Amount", help="- Other Income Amount - Code 40")

    # shr_opt_d1_ben_amt
    shr_opt_d1_ben_amt = fields.Float("Stock Option And Share Deduction 110(1) (d.1) Amount Before February 28, 2000",
                                      help="- Other Income Amount - Code 99, applies to year 2000 and prior")

    # sod_d1_a00_feb_amt
    sod_d1_a00_feb_amt = fields.Float("Security Options Deduction 110(1)(d.1)",
                                      help="- Other Income Amount - Code 41\nNote: Do not include this amount in box 14.")

    # empt_cmsn_amt
    empt_cmsn_amt = fields.Float("Employment Commission Amount", help="- Other Income Amount - Code 42")

    # cfppa_amt
    cfppa_amt = fields.Float("Canadian Armed Forces Personnel And Police Allowance",
                             help="- Other Income Amount - Code 43")

    # dfr_sob_amt
    dfr_sob_amt = fields.Float("Deferred Security Option Benefits", help="- Other Income Amount - Code 53")

    # empt_inc_amt_covid_prd1
    empt_inc_amt_covid_prd1 = fields.Float("Employment Income – March 15 To May 9 – 2020 Tax Year Only",
                                           help="- Other Income Amount - Code 57")

    # empt_inc_amt_covid_prd2
    empt_inc_amt_covid_prd2 = fields.Float("Employment income – May 10 To July 4 – 2020 Tax Year Only",
                                           help="- Other Income Amount - Code 58")

    # empt_inc_amt_covid_prd3
    empt_inc_amt_covid_prd3 = fields.Float("Employment Income – July 5 To August 29 – 2020 Tax Year Only",
                                           help="- Other Income Amount - Code 59")

    # empt_inc_amt_covid_prd4
    empt_inc_amt_covid_prd4 = fields.Float("Employment Income – August 30 To September 26 – 2020 Tax Year Only",
                                           help="- Other Income Amount - Code 60")

    # elg_rtir_amt
    elg_rtir_amt = fields.Float("Eligible Retiring Allowances",
                                help="- Other Income Amount – Code 66\n# Note: Do not include this amount in box 14.")

    # nelg_rtir_amt
    nelg_rtir_amt = fields.Float("Non-eligible Retiring Allowances",
                                 help="- Other Income Amount – Code 67\n# Note: Do not include this amount in box 14.")

    # indn_nelg_rtir_amt
    indn_nelg_rtir_amt = fields.Float("Status Indian Non-eligible Retiring Allowances",
                                      help="- Other Income Amount – Code 69\n# Note: Do not include this amount in box 14.")

    # indn_empe_amt
    indn_empe_amt = fields.Float("Status Indian Employee Amount",
                                 help="- Other Income Amount - Code 71\n# Note: If you are reporting this type of income, enter 0.00 in box 14.")

    # oc_incamt
    oc_incamt = fields.Float("Outside Of Canada Employment Income Amount- Section 122.3",
                             help="- Other Income Amount - Code 72")

    # oc_dy_cnt
    oc_dy_cnt = fields.Integer("Employment Outside Of Canada Day Count",
                               help="- 3 numeric\n- Other Income Field - Code 73")

    # pr_90_cntrbr_amt
    pr_90_cntrbr_amt = fields.Float("Pre-1990 Past Service Contributions While A Contributor",
                                    help="- Other Income Amount - Code 74")

    # pr_90_ncntrbr_amt
    pr_90_ncntrbr_amt = fields.Float("Pre-1990 Past Service Contributions While Not A Contributor",
                                     help="- Other Income Amount - Code 75")

    # cmpn_rpay_empr_amt
    cmpn_rpay_empr_amt = fields.Float("Workers’ Compensation Benefit Repaid To The Employer Amount",
                                      help="- Other Income Amount - Code 77\n# Note: Do not include this amount in box 14.")

    # fish_gro_ern_amt
    fish_gro_ern_amt = fields.Float("Fishers - Gross Earnings",
                                    help="- Other Income Amount - Code 78\n# Note: Do not include this amount in box 14.")

    # fish_net_ptnr_amt
    fish_net_ptnr_amt = fields.Float("Fishers - Net Partnership Amount",
                                     help="- Other Income Amount - Code 79\n# Note: Do not include this amount in box 14.")

    # fish_shr_prsn_amt
    fish_shr_prsn_amt = fields.Float("Fishers - Shareperson Amount",
                                     help="- Other Income Amount - Code 80\n# Note: Do not include this amount in box 14.")

    # plcmt_emp_agcy_amt
    plcmt_emp_agcy_amt = fields.Float("Placement Or Employment Agency",
                                      help="- Other Income Amount - Code 81\n# Note: Do not include this amount in box 14.")

    # drvr_taxis_oth_amt
    drvr_taxis_oth_amt = fields.Float("Driver Of Taxi Or Other Passenger-carrying Vehicle",
                                      help="- Other Income Amount - Code 82\nNote: Do not include this amount in box 14.")

    # brbr_hrdrssr_amt
    brbr_hrdrssr_amt = fields.Float("Barber Or Hairdresser",
                                    help="- Other Income Amount - Code 83\nNote: Do not include this amount in box 14.")

    # pub_trnst_pass_amt
    pub_trnst_pass_amt = fields.Float("Public Transit Pass", help="- Other Income Amount - Code 84")

    # epaid_hlth_pln_amt
    epaid_hlth_pln_amt = fields.Float("Employee-paid Premiums For Private Health Services Plans",
                                      help="- Other Income Amount - Code 85\nNote: Do not include this amount in box 14.")

    # stok_opt_csh_out_eamt
    stok_opt_csh_out_eamt = fields.Float("Stock Option Cash-out Expense", help="- Other Income Amount – Code 86")

    # vlntr_emergencyworker_xmpt_amt
    vlntr_emergencyworker_xmpt_amt = fields.Float("Emergency services volunteer exempt amount",
                                                  help="- Other Income Amount - Code 87\n- Valid for 2011 and subsequent tax years only\nNote: Do not include this amount in box 14.")

    # indn_txmpt_sei_amt
    indn_txmpt_sei_amt = fields.Float("Indian (Exempt Income) – Self-employment",
                                      help="- Other Income Amount - Code 88\nNote: Do not include this amount in box 14.")

    # ==================================== T4 Summary ===================================================
    # bn
    bn = fields.Char(
        string=" Employer Payroll Account Number",
        size=15,
        # required=True,
        help="- Required, 15 alphanumeric, 9 digits RP 4 digits, Example: 000000000RP0000"
    )

    # l1_nm
    employer_l1_nm = fields.Char(
        string="Employer Name - Line 1",
        size=30,
        # required=True,
        help="- Required 30 alphanumeric\n- first line of employer's name\n- if " '\n&' " is used in the name area enter as '&amp;'"
    )

    # l2_nm
    employer_l2_nm = fields.Char(
        string="Employer Name - Line 2",
        size=30,
        help="- 30 alphanumeric\n- Second line of employer's name"
    )

    # l3_nm
    employer_l3_nm = fields.Char(
        string="Employer Name - Line 3",
        size=30,
        help="- 30 alphanumeric\n- Use for 'care of' or 'attention'"
    )

    # addr_l1_txt
    employer_addr_l1_txt = fields.Char(
        string="Employer Address - Line 1",
        size=30,
        help="- 30 alphanumeric\n- First line of the employer's address"
    )

    # addr_l2_txt
    employer_addr_l2_txt = fields.Char(
        "Employer Address - Line 2",
        size=30,
        help="- 30 alphanumeric\n- Second line of the employer's address"
    )

    # cty_nm
    employer_cty_nm = fields.Char(
        "Employer City",
        size=28,
        help="- 28 alphanumeric\n- City in which the employer is located"
    )

    # prov_cd
    employer_prov_cd = fields.Char(
        "Employer Province Or Territory Code",
        size=2,
        help="- 2 alpha\n- Canadian province or territory in which the employer is located or the state in the USA where the employer is located. Use the abbreviations listed in the T619 - Electronic transmittal under section: Transmitter province or territory code. When the employer's country code is neither CAN nor USA, enter ZZ in this field."
    )

    # cntry_cd
    employer_cntry_cd = fields.Char(
        "Employer Country Code",
        size=3,
        help="- 3 alpha\n- Country in which the employer is located. Use the alphabetic country codes as outlined in the International Standard (ISO) 3166 Codes for the Representation of Names of Countries. Always use CAN for Canada, and USA for the United States of America."
    )

    # pstl_cd
    employer_pstl_cd = fields.Char("Employer postal code", size=10,
                                   help="Employer's Canadian postal code (format: alpha, numeric, alpha, numeric, alpha, numeric, example: A9A9A9) or the employer's USA zip code. When the employer's country code is neither CAN nor USA, enter the foreign postal code.")

    # cntc_nm
    cntc_nm = fields.Char(
        "Contact Name",
        size=22,
        # required=True,
        help="- Required, 22 alphanumeric\n- Contact's first name followed by surname for this return. Omit titles such as Mr., Mrs., etc."
    )

    # cntc_area_cd
    cntc_area_cd = fields.Char(
        "Contact Area Code",
        size=3,
        # required=True,
        help="- Required, 3 numeric\n- Area code of telephone number."
    )

    # cntc_phn_nbr
    cntc_phn_nbr = fields.Char(
        "Contact Telephone Number",
        size=8,
        # required=True,
        help="- Required, 3 numeric with a (-), followed by 4 numeric.\n- Telephone number of the contact (format: ###-####)."
    )

    # cntc_extn_nbr
    cntc_extn_nbr = fields.Char(
        "Contact Extension",
        size=5,
        help="- 5 numeric\n- Extension of the contact."
    )

    # tx_yr
    tx_yr = fields.Char(
        "Taxation Year",
        size=4,
        # required=True,
        help="- Required, 4 numeric\n- Taxation year (e.g., 2001)."
    )

    # slp_cnt
    slp_cnt = fields.Char(
        "Total Number Of T4 Slip Records",
        size=7,
        # required=True,
        help="- Required, 7 numeric\n- Total number of T4 slip records filed with this T4 Summary."
    )

    # pprtr_1_sin
    pprtr_1_sin = fields.Char(
        "Proprietor #1 Social Insurance Number (SIN)",
        size=9,
        # required=True,
        help="- Required, 9 numeric\n- If the employer is a Canadian-controlled private corporation or unincorporated, enter the SIN of the proprietor #1 or principal owner."
    )

    # pprtr_2_sin
    pprtr_2_sin = fields.Char(
        "Proprietor #2 Social Insurance Number (SIN)",
        size=9,
        help="- 9 numeric\n- If the employer is a Canadian-controlled private corporation or unincorporated, enter the SIN of the proprietor #2 or second principal owner."
    )

    # rpt_tcd
    rpt_tcd = fields.Selection(
        [("O", "Originals"), ("A", "Amendments")],
        default="O",
        string="Report Type Code",
        # required=True,
        help="- Required, 1 alpha\n- Originals = O\n- Amendments = A\n-Note: An amended return cannot contain an original slip."
    )

    # fileramendmentnote
    fileramendmentnote = fields.Char(
        "Filer Amendment Note",
        size=1309,
        help="Use for report type A only.\n- 1309 alphanumeric"
    )

    # tot_empt_incamt
    tot_empt_incamt = fields.Float(
        string="Total Employment Income",
        help="- 13 numeric\n- Accumulated total of employees' income"
    )

    # tot_empe_cpp_amt
    tot_empe_cpp_amt = fields.Float(
        string="Total Employees' Canada Pension Plan Contributions",
        help="- 11 numeric\n- Accumulated total of employees' Canada Pension Plan contributions"
    )

    # tot_empe_cppe_amt
    tot_empe_cppe_amt = fields.Float(
        string="Total Employees' Second Pension Plan Contributions",
        help="""- 11 numeric
        - Accumulated total of employees' second Canada Pension Plan contributions
        Note: Do not include the total employees' second Quebec Pension Plan contributions in this field."""
    )

    # tot_empe_eip_amt
    tot_empe_eip_amt = fields.Float(
        string="Total Employees' Employment Insurance Premiums",
        help="- 11 numeric\n- Accumulated total of employees' Employment Insurance premiums"
    )

    # tot_rpp_cntrb_amt
    tot_rpp_cntrb_amt = fields.Float(
        string="Total Registered Pension Plan Contributions",
        help="- 11 numeric\n- Accumulated total of employees' registered pension plan contributions"
    )

    # tot_itx_ddct_amt
    tot_itx_ddct_amt = fields.Float(
        string="Total Income Tax Deducted",
        help="- 13 numeric\n- Accumulated total of employees' income tax deductions"
    )

    # tot_padj_amt
    tot_padj_amt = fields.Float(
        string="Total Pension Adjustment",
        help="- 13 numeric\n- Accumulated total of employees' pension adjustment"
    )

    # tot_empr_cpp_amt
    tot_empr_cpp_amt = fields.Float(
        string="Total Employer's Canada Pension Plan Contributions", help="- 11 numeric"
    )
    # tot_empr_cppe_amt
    tot_empr_cppe_amt = fields.Float(
        string="Total Employer's Second Pension Plan Contributions", help="""- 11 numeric"""
    )

    # tot_empr_eip_amt
    tot_empr_eip_amt = fields.Float(
        string="Total Employer's Employment Insurance Premiums", help="- 11 numeric"
    )


    def open_t4_website(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.canada.ca/en/revenue-agency/services/e-services/e-services-businesses/business-account.html',
            'target': 'new',
        }

    @api.onchange('employee_id')
    def _onchage_contract_ids(self):
        contract_domain_id = self.env['hr.version'].search([
            ('company_id', '=', self.company_id.id),
            ('employee_id', '=', self.employee_id.id),
            ('active', '!=', False),
            # ('date_start', '<=', payslip.date_to),
            # '|',
            # ('date_end', '>=', payslip.date_from),
            # ('date_end', '=', False)
        ])
        self.employee_contract = contract_domain_id

        # return [('id', 'in',contract_domain_ids.ids )]

    # ============================ Base Functions ==================================
    @api.constrains('employee_id', 'year')
    def _check_employee_and_year(self):
        self.ensure_one()
        records_count = self.search_count([('employee_id', '=', self.employee_id.id), ('year', '=', self.year)])
        if records_count > 1:
            raise UserError(_("Duplicate Error: Record already exists."))

    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.year:
                rec.display_name= str(rec.name) + "-" + str(rec.year)
            else:
                super()._compute_display_name()




    # ========================== Compute T4 ======================================
    def _get_all_t4_amount(self):
        # Employee Payslip
        employee_payslip_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ('state', '=', 'paid')])
        year_specific_employee_payslip_ids = employee_payslip_ids.filtered(
            lambda s: s.date_from.year == int(self.year) or s.date_to.year == int(self.year))
        emp_line_obj = self.employee_id.payroll_line_ids.filtered(lambda x: x.year == self.year)

        employee_contract = self.employee_contract
        t4_amount = {}
        cpp_cnt_amount = 0.0
        cpp_cnt_amount = 0.0
        cppe_cntrb_amt = 0.0 # CPP2 amount
        qppe_cntrb_amt = 0.0 # Quebec CPP2 amount
        qpp_cnt_amount = 0.0
        canada_cpp_qpp_ern_amt = 0.0
        employee_empt_incamt = 0.0
        employee_empe_eip_amt = 0.0
        employer_empe_eip_amt = 0.0
        employee_ei_insu_ern_amt = 0.0
        income_itx_ddct_amt = 0.0
        union_unn_dues_amt = 0.0
        charitable_chrty_dons_amt = 0.0
        pension_padj_amt = 0.0
        PPIP_prov_pip_amt = 0.0
        PPIP_prov_insu_ern_amt = 0.0
        empt_cmsn_amt = 0.0

        for pay in year_specific_employee_payslip_ids:
            for line in pay.line_ids:
                # if line.code == 'CPP_QPP_EA':
                #     canada_cpp_qpp_ern_amt += line.amount
                if line.code == 'CPP':
                    cpp_cnt_amount += line.amount
                elif line.code == 'CPP2':
                    cppe_cntrb_amt += line.amount
                elif line.code == 'I_Earning': #This will be total gross amount (GROSS + ALW + ADD_ALW)
                    employee_empt_incamt += line.amount
                # elif line.code == 'EI_EA':
                #
                #     employee_ei_insu_ern_amt += line.amount
                elif line.code == 'EI':
                    employee_empe_eip_amt += line.amount
                elif line.code == 'EI_EMPLOYER':
                    employer_empe_eip_amt += line.amount
                elif line.code in ['FTAX', 'OTAX']:
                    income_itx_ddct_amt += line.amount
                elif line.code == 'UNION_DUES':
                    union_unn_dues_amt += line.amount
                elif line.code == 'CHAR_DON':
                    charitable_chrty_dons_amt += line.amount
                elif line.code == 'PEN_ADJ':
                    pension_padj_amt += line.amount
                elif line.code == 'PPI_EARN':
                    PPIP_prov_insu_ern_amt += line.amount
                elif line.code == 'PPI_PRE':
                    PPIP_prov_pip_amt += line.amount
                elif line.code == 'COMMISSION':
                    empt_cmsn_amt += line.amount

            # if
            # cpp_cnt_amount +=
        # Total Insurable earning with previous amount
        employee_empt_incamt +=  emp_line_obj.ytd_previous_pi if emp_line_obj else 0

        t4_amount.update({
            'employee_empt_incamt': round(employee_empt_incamt,2),
            'tot_empt_incamt': round(employee_empt_incamt,2),
            'income_itx_ddct_amt': round(income_itx_ddct_amt,2),
            'tot_itx_ddct_amt': round(income_itx_ddct_amt,2),
            'union_unn_dues_amt': round(union_unn_dues_amt,2),
            'charitable_chrty_dons_amt': round(charitable_chrty_dons_amt,2),
            'pension_padj_amt': round(pension_padj_amt,2),
            'empt_cmsn_amt' :round(empt_cmsn_amt,2)
        })
        if not employee_contract.is_cpp_qpp_xmpt_cd:
            canada_cpp_qpp_ern_amt = round(employee_empt_incamt, 2)
            # Total CPP with previous amount

            cpp_cnt_amount += emp_line_obj.ytd_previous_cpp if emp_line_obj else 0

            # Total CPP2 with previous amount
            cppe_cntrb_amt += emp_line_obj.ytd_previous_cpp2 if emp_line_obj else 0
            t4_amount.update(
                {
                  'employee_cpp_cntrb_amt': round(cpp_cnt_amount,2),
                  'employee_cppe_cntrb_amt': round(cppe_cntrb_amt,2),
                 'tot_empe_cpp_amt': round(cpp_cnt_amount,2),
                 'tot_empr_cpp_amt': round(cpp_cnt_amount,2),
                #CPP2
                'tot_empe_cppe_amt': round(cppe_cntrb_amt, 2),
                'tot_empr_cppe_amt': round(cppe_cntrb_amt, 2),
                 'canada_cpp_qpp_ern_amt': round(canada_cpp_qpp_ern_amt,2)}
            )
        if not employee_contract.is_ei_xmpt_cd:
            employee_ei_insu_ern_amt = round(employee_empt_incamt, 2)
            # Total Employee EI with previous amount
            line_obj = self.employee_id.payroll_line_ids.filtered(lambda x: x.year == self.year)
            employee_empe_eip_amt += line_obj.ytd_previous_ei if line_obj else 0
            # Total Employer EI with previous amount
            employer_empe_eip_amt += line_obj.ytd_previous_ei_employer if line_obj else 0
            t4_amount.update(
                {'employee_empe_eip_amt': round(employee_empe_eip_amt,2),
                 'tot_empe_eip_amt': round(employee_empe_eip_amt,2),
                 'tot_empr_eip_amt': round(employer_empe_eip_amt,2),
                 'employee_ei_insu_ern_amt': round(employee_ei_insu_ern_amt,2)}
            )
        if not employee_contract.is_prov_pip_xmpt_cd:
            t4_amount.update(
                {'PPIP_prov_pip_amt': round(PPIP_prov_pip_amt,2),
                 'PPIP_prov_insu_ern_amt': round(PPIP_prov_insu_ern_amt,2)}
            )

        return t4_amount

    def compute_t4(self):
        if self.employee_id:
            employee = self.employee_id
            employee_contract = self.employee_contract
            # employee_home_add = employee.private_street
            employeer = self.company_id.partner_id
            employeer_contact_id = employeer.employeer_contact_id

            payload = self._get_all_t4_amount()
            payload.update({
                'employee_snm': employee.name.split(" ")[-1],  # FIX: Add field on employee
                'employee_gvn_nm': employee.name.split(" ")[0],  # FIX: Add field on employee
                'employee_init': employee.name.split(" ")[0][0],  # Need to sure and add field to employee

                # Employee Home Address
                "employee_addr_l1_txt": employee.private_street,
                "employee_addr_l2_txt": employee.private_street2,
                "employee_cty_nm": employee.private_city,
                "employee_prov_cd": employee.private_state_id.code,
                "employee_cntry_cd": 'CAN',
                "employee_pstl_cd": employee.private_zip,

                # Employee T4slip
                "employee_sin": str(employee.identification_id) or '',
                "employee_empe_nbr": employee.barcode,
                "employee_bn": employee.company_id.payroll_account_number,
                "employee_rpp_dpsp_rgst_nbr": employee.employee_prpp_dpsp_rgst_nbr,
                "employee_cpp_qpp_xmpt_cd": '0' if employee_contract.is_cpp_qpp_xmpt_cd else '1',
                "employee_ei_xmpt_cd": '0' if employee_contract.is_ei_xmpt_cd else '1',
                "employee_prov_pip_xmpt_cd": '0' if employee_contract.is_prov_pip_xmpt_cd else '1',
                "employee_empt_prov_cd": employeer.state_id.code,

                # T4 Summary
                'bn': self.company_id.payroll_account_number,
                'employer_l1_nm': employeer.company_name1,
                'employer_l2_nm': employeer.company_name2,
                'employer_l3_nm': employeer.company_name3,

                "employer_addr_l1_txt": employeer.street,
                "employer_addr_l2_txt": employeer.street2,
                "employer_cty_nm": employeer.city,
                "employer_prov_cd": employeer.state_id.code,
                "employer_cntry_cd": 'CAN',
                "employer_pstl_cd": employeer.zip,

                "cntc_nm": employeer_contact_id.name or '',
                "cntc_area_cd": employeer_contact_id.zip or '',
                "cntc_phn_nbr": employeer_contact_id.phone or '',
                "cntc_extn_nbr": employeer.cntc_extn_nbr or '',
                # "cntc_phn_nbr": employeer_contact_id.phone or '',
                "slp_cnt": '1',
                "tx_yr": self.year,
                "pprtr_1_sin": str(employeer.employeer_pprtr_1_sin) or "",
                "pprtr_2_sin": str(employeer.employeer_pprtr_2_sin) or "",
                # "rpt_tcd": self.employee_rpt_tcd if self.employee_rpt_tcd == 'A' else None,

            })

            self.write(payload)

        # return None

    # ======================== Generate and download T4 xml ===========================
    def download_t4_xml(self):
        # Generate the T4 XML content
        kwrgs=[]
        domain = []
        for employee in self:
            filename = f'{employee.employee_id.name}'+ f'{employee.year}'+ '_T4' + '.xml'
            # for rec in self:
            xml_content = employee.generate_t4_xml(employee)
            employee.xml_content = xml_content

            content_type = 'application/xml'

            kwrgs.append((xml_content,filename, content_type))

            return {
                'type': 'ir.actions.act_url',
                'url': '/download/remuneration/?model=statement.remuneration&field=xml_content&id=%s&filename=%s&content_type=%s' % (
                    employee.id, filename, content_type),
                'target': 'self',
            }

    def create_t4_xml(self,employees):
        tot_empt_incamt_sum = 0
        tot_empe_cpp_amt_sum = 0
        tot_empe_cppe_amt_sum = 0
        tot_empe_eip_amt_sum = 0
        tot_rpp_cntrb_amt_sum = 0
        tot_itx_ddct_amt_sum = 0
        tot_padj_amt_sum = 0
        tot_empr_cpp_amt_sum = 0
        tot_empr_cppe_amt_sum = 0
        tot_empr_eip_amt_sum = 0


        employee_act =  self.search([('id', '=', self.env.context.get('active_id'))]) if self.env.context.get('active_id') else self

        # Create the root element
        root = ET.Element("Return")

        # Create the T4 element
        t4 = ET.SubElement(root, "T4")

        # Create the T4Slip element

        for employee in employees:
            t4_slip = ET.SubElement(t4, "T4Slip")
            # Add EMPE_NM subelement
            empe_nm = ET.SubElement(t4_slip, "EMPE_NM")
            ET.SubElement(empe_nm, "snm").text = employee.employee_snm
            ET.SubElement(empe_nm, "gvn_nm").text = employee.employee_gvn_nm
            ET.SubElement(empe_nm, "init").text = employee.employee_init

            # Add EMPE_ADDR subelement
            empe_addr = ET.SubElement(t4_slip, "EMPE_ADDR")
            ET.SubElement(empe_addr, "addr_l1_txt").text = employee.employee_addr_l1_txt
            ET.SubElement(empe_addr, "addr_l2_txt").text = employee.employee_addr_l2_txt
            ET.SubElement(empe_addr, "cty_nm").text = employee.employee_cty_nm
            ET.SubElement(empe_addr, "prov_cd").text = employee.employee_prov_cd
            ET.SubElement(empe_addr, "cntry_cd").text = employee.employee_cntry_cd
            ET.SubElement(empe_addr, "pstl_cd").text = employee.employee_pstl_cd

            # Add other subelements
            ET.SubElement(t4_slip, "sin").text = str(employee.employee_sin or '')
            ET.SubElement(t4_slip, "empe_nbr").text = str(employee.employee_empe_nbr or '') or ''
            ET.SubElement(t4_slip, "bn").text = str(employee.employee_bn or '')
            ET.SubElement(t4_slip, "rpp_dpsp_rgst_nbr").text = str(employee.employee_rpp_dpsp_rgst_nbr or '')
            ET.SubElement(t4_slip, "cpp_qpp_xmpt_cd").text = str(employee.employee_cpp_qpp_xmpt_cd or '')
            ET.SubElement(t4_slip, "ei_xmpt_cd").text = str(employee.employee_ei_xmpt_cd or '')
            ET.SubElement(t4_slip, "prov_pip_xmpt_cd").text = str(employee.employee_prov_pip_xmpt_cd or '')
            ET.SubElement(t4_slip, "empt_cd").text = str(employee.employee_empt_cd or '')
            ET.SubElement(t4_slip, "rpt_tcd").text = str(employee.employee_rpt_tcd or '') or ''
            ET.SubElement(t4_slip, "empt_prov_cd").text = str(employee.employee_empt_prov_cd or '')
            ET.SubElement(t4_slip, "empr_dntl_ben_rpt_cd").text = str(employee.empr_dntl_ben_rpt_cd or '')

            # Add T4_AMT subelement
            t4_amt = ET.SubElement(t4_slip, "T4_AMT")
            ET.SubElement(t4_amt, "empt_incamt").text = str(employee.employee_empt_incamt or '')
            ET.SubElement(t4_amt, "cpp_cntrb_amt").text = str(employee.employee_cpp_cntrb_amt or '')
            ET.SubElement(t4_amt, "cppe_cntrb_amt").text = str(employee.employee_cppe_cntrb_amt or '')
            ET.SubElement(t4_amt, "qpp_cntrb_amt").text = str(employee.employee_qpp_cntrb_amt or '')
            ET.SubElement(t4_amt, "qppe_cntrb_amt").text = str(employee.employee_qppe_cntrb_amt or '')
            ET.SubElement(t4_amt, "empe_eip_amt").text = str(employee.employee_empe_eip_amt or '')
            ET.SubElement(t4_amt, "rpp_cntrb_amt").text = str(employee.registered_rpp_cntrb_amt or '')
            ET.SubElement(t4_amt, "itx_ddct_amt").text = str(employee.income_itx_ddct_amt or '')
            ET.SubElement(t4_amt, "ei_insu_ern_amt").text = str(employee.employee_ei_insu_ern_amt or '')
            ET.SubElement(t4_amt, "cpp_qpp_ern_amt").text = str(employee.canada_cpp_qpp_ern_amt or '')
            ET.SubElement(t4_amt, "unn_dues_amt").text = str(employee.union_unn_dues_amt or '')
            ET.SubElement(t4_amt, "chrty_dons_amt").text = str(employee.charitable_chrty_dons_amt or '')
            ET.SubElement(t4_amt, "padj_amt").text = str(employee.pension_padj_amt or '')
            ET.SubElement(t4_amt, "prov_pip_amt").text = str(employee.PPIP_prov_pip_amt or '')
            ET.SubElement(t4_amt, "prov_insu_ern_amt").text = str(employee.PPIP_prov_insu_ern_amt or '')

            # Add OTH_INFO subelement
            oth_info = ET.SubElement(t4_slip, "OTH_INFO")
            ET.SubElement(oth_info, "hm_brd_lodg_amt").text = str(employee.hm_brd_lodg_amt or '')
            ET.SubElement(oth_info, "spcl_wrk_site_amt").text = str(employee.spcl_wrk_site_amt or '')
            ET.SubElement(oth_info, "prscb_zn_trvl_amt").text = str(employee.prscb_zn_trvl_amt or '')
            ET.SubElement(oth_info, "med_trvl_amt").text = str(employee.med_trvl_amt or '')
            ET.SubElement(oth_info, "prsnl_vhcl_amt").text = str(employee.prsnl_vhcl_amt or '')
            ET.SubElement(oth_info, "rsn_per_km_amt").text = str(employee.rsn_per_km_amt or '')
            ET.SubElement(oth_info, "low_int_loan_amt").text = str(employee.low_int_loan_amt or '')
            ET.SubElement(oth_info, "empe_hm_loan_amt").text = str(employee.empe_hm_loan_amt or '')
            ET.SubElement(oth_info, "stok_opt_ben_amt").text = str(employee.stok_opt_ben_amt or '')
            ET.SubElement(oth_info, "sob_a00_feb_amt").text = str(employee.sob_a00_feb_amt or '')
            ET.SubElement(oth_info, "shr_opt_d_ben_amt").text = str(employee.shr_opt_d_ben_amt or '')
            ET.SubElement(oth_info, "sod_d_a00_feb_amt").text = str(employee.sod_d_a00_feb_amt or '')
            ET.SubElement(oth_info, "oth_tx_ben_amt").text = str(employee.oth_tx_ben_amt or '')
            ET.SubElement(oth_info, "shr_opt_d1_ben_amt").text = str(employee.shr_opt_d1_ben_amt or '')
            ET.SubElement(oth_info, "sod_d1_a00_feb_amt").text = str(employee.sod_d1_a00_feb_amt or '')
            ET.SubElement(oth_info, "empt_cmsn_amt").text = str(employee.empt_cmsn_amt or '')
            ET.SubElement(oth_info, "cfppa_amt").text = str(employee.cfppa_amt or '')
            ET.SubElement(oth_info, "dfr_sob_amt").text = str(employee.dfr_sob_amt or '')
            ET.SubElement(oth_info, "empt_inc_amt_covid_prd1").text = str(employee.empt_inc_amt_covid_prd1 or '')
            ET.SubElement(oth_info, "empt_inc_amt_covid_prd2").text = str(employee.empt_inc_amt_covid_prd2 or '')
            ET.SubElement(oth_info, "empt_inc_amt_covid_prd3").text = str(employee.empt_inc_amt_covid_prd3 or '')
            ET.SubElement(oth_info, "empt_inc_amt_covid_prd4").text = str(employee.empt_inc_amt_covid_prd4 or '')
            ET.SubElement(oth_info, "elg_rtir_amt").text = str(employee.nelg_rtir_amt or '')
            ET.SubElement(oth_info, "nelg_rtir_amt").text = str(employee.indn_nelg_rtir_amt or '')
            ET.SubElement(oth_info, "indn_nelg_rtir_amt").text = str(employee.indn_nelg_rtir_amt or '')
            ET.SubElement(oth_info, "indn_empe_amt").text = str(employee.indn_empe_amt or '')
            ET.SubElement(oth_info, "oc_incamt").text = str(employee.oc_incamt or '')
            ET.SubElement(oth_info, "oc_dy_cnt").text = str(employee.oc_dy_cnt or '')
            ET.SubElement(oth_info, "pr_90_cntrbr_amt").text = str(employee.pr_90_cntrbr_amt or '')
            ET.SubElement(oth_info, "pr_90_ncntrbr_amt").text = str(employee.pr_90_ncntrbr_amt or '')
            ET.SubElement(oth_info, "cmpn_rpay_empr_amt").text = str(employee.cmpn_rpay_empr_amt or '')
            ET.SubElement(oth_info, "fish_gro_ern_amt").text = str(employee.fish_gro_ern_amt or '')
            ET.SubElement(oth_info, "fish_net_ptnr_amt").text = str(employee.fish_net_ptnr_amt or '')
            ET.SubElement(oth_info, "fish_shr_prsn_amt").text = str(employee.fish_shr_prsn_amt or '')
            ET.SubElement(oth_info, "plcmt_emp_agcy_amt").text = str(employee.plcmt_emp_agcy_amt or '')
            ET.SubElement(oth_info, "drvr_taxis_oth_amt").text = str(employee.drvr_taxis_oth_amt or '')
            ET.SubElement(oth_info, "brbr_hrdrssr_amt").text = str(employee.brbr_hrdrssr_amt or '')
            ET.SubElement(oth_info, "pub_trnst_pass_amt").text = str(employee.pub_trnst_pass_amt or '')
            ET.SubElement(oth_info, "epaid_hlth_pln_amt").text = str(employee.epaid_hlth_pln_amt or '')
            ET.SubElement(oth_info, "stok_opt_csh_out_eamt").text = str(employee.stok_opt_csh_out_eamt or '')
            ET.SubElement(oth_info, "vlntr_emergencyworker_xmpt_amt").text = str(employee.vlntr_emergencyworker_xmpt_amt or '')
            ET.SubElement(oth_info, "indn_txmpt_sei_amt").text = str(employee.indn_txmpt_sei_amt or '')

            tot_empt_incamt_sum += employee.tot_empt_incamt
            tot_empe_cpp_amt_sum += employee.tot_empe_cpp_amt
            tot_empe_cppe_amt_sum += employee.tot_empe_cppe_amt
            tot_empe_eip_amt_sum += employee.tot_empe_eip_amt
            tot_rpp_cntrb_amt_sum += employee.tot_rpp_cntrb_amt
            tot_itx_ddct_amt_sum += employee.tot_itx_ddct_amt
            tot_padj_amt_sum += employee.tot_padj_amt
            tot_empr_cpp_amt_sum += employee.tot_empr_cpp_amt
            tot_empr_cppe_amt_sum += employee.tot_empr_cppe_amt
            tot_empr_eip_amt_sum += employee.tot_empr_eip_amt

        # Create T4Summary element
        t4_summary = ET.SubElement(t4, "T4Summary")
        ET.SubElement(t4_summary, "bn").text = str(self.bn or '') or ''

        # Add EMPR_NM subelement
        empr_nm = ET.SubElement(t4_summary, "EMPR_NM")
        ET.SubElement(empr_nm, "l1_nm").text = str(employee_act.employer_l1_nm or '')
        ET.SubElement(empr_nm, "l2_nm").text = str(employee_act.employer_l2_nm or '')
        ET.SubElement(empr_nm, "l3_nm").text = str(employee_act.employer_l3_nm or '')

        # Add EMPR_ADDR subelement
        empr_addr = ET.SubElement(t4_summary, "EMPR_ADDR")
        ET.SubElement(empr_addr, "addr_l1_txt").text = str(employee_act.employer_addr_l1_txt or '')
        ET.SubElement(empr_addr, "addr_l2_txt").text = str(employee_act.employer_addr_l2_txt or '')
        ET.SubElement(empr_addr, "cty_nm").text = str(employee_act.employer_cty_nm or '')
        ET.SubElement(empr_addr, "prov_cd").text = str(employee_act.employer_prov_cd or '')
        ET.SubElement(empr_addr, "cntry_cd").text = str(employee_act.employer_cntry_cd or '')
        ET.SubElement(empr_addr, "pstl_cd").text = str(employee_act.employer_pstl_cd or '')

        # Add CNTC subelement
        cntc = ET.SubElement(t4_summary, "CNTC")
        ET.SubElement(cntc, "cntc_nm").text = str(employee_act.cntc_nm or '')
        ET.SubElement(cntc, "cntc_area_cd").text = str(employee_act.cntc_area_cd or '')
        ET.SubElement(cntc, "cntc_phn_nbr").text = str(employee_act.cntc_phn_nbr or '')
        ET.SubElement(cntc, "cntc_extn_nbr").text = str(employee_act.cntc_extn_nbr or '')

        ET.SubElement(t4_summary, "tx_yr").text = str(employee_act.tx_yr or '')
        ET.SubElement(t4_summary, "slp_cnt").text = str(employee_act.slp_cnt or '')

        # Add PPRTR_SIN subelement
        pprtr_sin = ET.SubElement(t4_summary, "PPRTR_SIN")
        ET.SubElement(pprtr_sin, "pprtr_1_sin").text = str(employee_act.pprtr_1_sin or '')
        ET.SubElement(pprtr_sin, "pprtr_2_sin").text = str(employee_act.pprtr_2_sin or '')

        ET.SubElement(t4_summary, "rpt_tcd").text = str(employee_act.rpt_tcd or 'O')
        ET.SubElement(t4_summary, "fileramendmentnote").text = str(employee_act.fileramendmentnote or '')

        # Add T4_TAMT subelement
        t4_tamt = ET.SubElement(t4_summary, "T4_TAMT")
        ET.SubElement(t4_tamt, "tot_empt_incamt").text = str(tot_empt_incamt_sum or '')
        ET.SubElement(t4_tamt, "tot_empe_cpp_amt").text = str(tot_empe_cpp_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_empe_cppe_amt").text = str(tot_empe_cppe_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_empe_eip_amt").text = str(tot_empe_eip_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_rpp_cntrb_amt").text = str(tot_rpp_cntrb_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_itx_ddct_amt").text = str(tot_itx_ddct_amt_sum or '')
        # ET.SubElement(t4_tamt, "tot_ei_insu_ern_amt").text = "2000.00"
        # ET.SubElement(t4_tamt, "tot_cpp_qpp_ern_amt").text = "3000.00"
        # ET.SubElement(t4_tamt, "tot_unn_dues_amt").text = "100.00"
        # ET.SubElement(t4_tamt, "tot_chrty_dons_amt").text = "200.00"
        ET.SubElement(t4_tamt, "tot_padj_amt").text = str(tot_padj_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_empr_cpp_amt").text = str(tot_empr_cpp_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_empr_cppe_amt").text = str(tot_empr_cppe_amt_sum or '')
        ET.SubElement(t4_tamt, "tot_empr_eip_amt").text = str(tot_empr_eip_amt_sum or '')
        # ET.SubElement(t4_tamt, "tot_prov_pip_amt").text = "100.00"
        # ET.SubElement(t4_tamt, "tot_prov_insu_ern_amt").text = "1000.00"

        # Create the XML tree
        tree = ET.ElementTree(root)

        # Convert the XML tree to a string
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)

        # Return the XML string
        return xml_str.decode()

    def generate_t4_xml(self,employees):
        # Call the function you created in step 2 to generate the T4 XML content
        xml_content = self.create_t4_xml(employees)
        return xml_content

    # ======================== Generate and download T4 PDF ===========================
    def download_t4_pdf(self):

       for rec in self:
            kwrgs = rec.generate_data_for_pdf(rec)
            pdf_name = str(
                datetime.datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-{rec.year}-")) + str(
                datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".pdf"

       return {
            'type': 'ir.actions.act_url',
            'url': '/download/pdf?file_path=%s&file_name=%s&file_paths=%s' % ('', pdf_name, kwrgs),
            'target': 'new',
        }
    def generate_data_for_pdf(self,employees):
        kwrgs = []
        for rec in employees:
            if rec.state == 'done':
                try:
                    pdf_template_path = file_path(
                        'syncoria_can_payroll/utils/t4-fill-23e.pdf'
                    )

                    output_folder_path = os.path.expanduser(os.getenv("HOME")) + "/outPdf/"
                    if not os.path.isdir(output_folder_path):
                        os.mkdir(output_folder_path)

                    pdf_name = str(
                        datetime.datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-{rec.year}-")) + str(
                        datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".pdf"
                    filename = output_folder_path + pdf_name

                    reader = PdfReader(pdf_template_path)
                    # fields = reader.get_fields()
                    # print(fields)
                    writer = PdfWriter()

                    writer.append(reader)

                    # Constructing the data dictionary
                    data = {'Slip1Year[0]': rec.year,
                            'Slip1EmployersName[0]': f'{rec.employer_l1_nm}\n{rec.employer_addr_l1_txt}\n{rec.employer_cty_nm},{rec.employer_prov_cd} {rec.employer_pstl_cd}',
                            'Slip1Box54[0]': rec.employee_bn,
                            'Slip1Box12[0]': rec.employee_sin, 'Slip1Box14[0]': round(rec.employee_empt_incamt, 2),
                            'Slip1Box22[0]': round(rec.income_itx_ddct_amt, 2), 'Slip1Box10[0]': 'ON',
                            'DropDownList[0]': rec.empr_dntl_ben_rpt_cd or "1",
                            'Slip1Box16[0]': round(rec.employee_cpp_cntrb_amt, 2),
                            'Slip1Box29[0]': rec.employee_empt_cd or "11",
                            'Slip1CPP[0]': int(rec.employee_cpp_qpp_xmpt_cd),
                            'Slip1EI[0]': int(rec.employee_ei_xmpt_cd),
                            'Slip1PPIP[0]': int(rec.employee_prov_pip_xmpt_cd),
                            'Slip1Box16A[0]': round(rec.employee_cppe_cntrb_amt, 2),
                            'Slip1Box24[0]': round(rec.employee_ei_insu_ern_amt, 2), 'Slip1Box17[0]': 0.0,
                            'Slip1Box26[0]': round(rec.canada_cpp_qpp_ern_amt, 2),
                            'Slip1Box18[0]': rec.employee_empe_eip_amt,
                            'Slip1Box44[0]': rec.union_unn_dues_amt, 'Slip1Box20[0]': 0.0,
                            'Slip1Box46[0]': rec.charitable_chrty_dons_amt, 'Slip1Box52[0]': rec.pension_padj_amt,
                            'Slip1Box50[0]': rec.employee_rpp_dpsp_rgst_nbr, 'Slip1Box55[0]': rec.PPIP_prov_pip_amt,
                            'Slip1Box56[0]': rec.PPIP_prov_insu_ern_amt, 'Slip1LastName[0]': rec.employee_snm,
                            'Slip1FirstName[0]': rec.employee_gvn_nm, 'Slip1Initial[0]': rec.employee_init,
                            'Slip1Address[0]': f'{rec.employee_addr_l1_txt}\n{rec.employee_addr_l2_txt}\n{rec.employee_cty_nm}\n{rec.employee_prov_cd} {rec.employee_pstl_cd}',
                            'Slip1Amount1[0]': rec.empt_cmsn_amt,
                            'Slip1Box1[0]': '42',
                            'Slip1Amount2[0]': None, 'Slip1Amount3[0]': None, 'Slip1Amount4[0]': None,
                            'Slip1Amount5[0]': None,
                            'Slip1Amount6[0]': None, 'Slip1EmployersName[0].2': None,
                            'Slip1Year[0].2': None, 'Slip1Box54[0].2': None, 'Slip1Box12[0].2': None,
                            'Slip1Box14[0].2': None,
                            'Slip1Box22[0].2': None, 'Slip1Box16[0].2': None, 'Slip1Box24[0].2': None,
                            'Slip1Box17[0].2': None, 'Slip1Box17A[0].2': None,
                            'Slip1Box26[0].2': None, 'Slip1Box18[0].2': None, 'Slip1Box44[0].2': None,
                            'Slip1Box20[0].2': None,
                            'Slip1Box46[0].2': None, 'Slip1Box52[0].2': None, 'Slip1Box50[0].2': None,
                            'Slip1Box55[0].2': None,
                            'Slip1Box56[0].2': None, 'Slip1LastName[0].2': None, 'Slip1FirstName[0].2': None,
                            'Slip1Initial[0].2': None, 'Slip1Address[0].2': None, 'Slip1Amount1[0].2': None,
                            'Slip1Amount2[0].2': None, 'Slip1Amount3[0].2': None, 'Slip1Amount4[0].2': None,
                            'Slip1Amount5[0].2': None, 'Slip1Amount6[0].2': None}

                    # Handle None values
                    data = {key: str(value) if value is not None else "" for key, value in data.items()}

                    writer.update_page_form_field_values(writer.pages[0], data)

                    # Write the updated PDF to a file
                    with open(filename, "wb") as output_stream:
                        writer.write(output_stream)
                except PermissionError as pe:
                    raise UserError(_(f"Permission Error: {pe}"))
                except IOError as ie:
                    raise UserError(_(f"IO Error: {ie}"))
                # Uncomment for general error handling if needed
                except Exception as e:
                    raise UserError(_(f"Internal Error: {e}"))

                kwrgs.append((filename, pdf_name))
        return kwrgs

    # def send_t4_xml_batch(self):
    #     files_list=[]
    #     mail_template = self.env.ref('syncoria_can_payroll.email_template_batch_xml')
    #     for rec in self:
    #         xml_content = rec.generate_t4_xml()
    #         rec.xml_content = xml_content
    #
    #         attachment = self.env['ir.attachment'].create({
    #             'name': str(
    #                     datetime.datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-{rec.year}-")) + str(
    #                     datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".xml",
    #             'raw': xml_content,
    #             'res_id': rec.id,
    #             'res_model': 'statement.remuneration',
    #             'type': 'binary',
    #             'mimetype': 'application/xml',
    #         })
    #         files_list.append((4, attachment.id))
    #
    #     # mail_template.attachment_ids = files_list
    #     email_values = {
    #         "attachment_ids": files_list
    #     }
    #
    #     try:
    #         mail_template.send_mail(rec.id, force_send=True, raise_exception=True,email_values=email_values)
    #         message = "Your email has been sent."
    #         notification_type = 'success'
    #     except Exception as e:
    #         message = f"Error occurred while sending email: {str(e)}"
    #         notification_type = 'danger'
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'message': message,
    #             'type': notification_type,
    #             'sticky': True,
    #         }
    #     }

    def action_open_t4_message_wizard(self):
        # This method will be called when the server action is executed
        return {
            'name': 'T4 Batch Message Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 't4.messeage.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('syncoria_can_payroll.view_t4_messeage_wizard_form').id,
            'target': 'new',  # This opens the wizard in a popup
        }


