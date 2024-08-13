# -*- coding: utf-8 -*-
import os

from odoo import models, fields, api, _
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError

from odoo.modules.module import get_module_resource
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
    #     comodel_name='hr.contract',
    #     string='Employee Contract',
    #     required=True,
    #     # domain=lambda self: self._domain_contract_ids(),
    #     # domain=[('employee_id','=' ,employee_id)],
    # )
    employee_contract = fields.Many2one('hr.contract', string="Employee Contract")

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
    employee_snm = fields.Char("Employee surname", size=20, help="- first 20 letters of the employee's surname\
    - omit titles such as Mr., Mrs., etc.\
    - do not include first name or initials")

    employee_gvn_nm = fields.Char("Employee first name", size=12,
                                  help="-first 12 letters of the employee's first given name")

    employee_init = fields.Char(" Employee Initial", size=1, help="- initial of the employee's second given name")
    employee_addr_l1_txt = fields.Char("Employee address - line 1", size=30,
                                       help="- first line of the employee's address")
    employee_addr_l2_txt = fields.Char("Employee address - line 2", size=30,
                                       help="- second line of the employee's address")
    employee_cty_nm = fields.Char("Employee city", size=28, help="- city in which the employee is located.")
    employee_prov_cd = fields.Char("Employee province or territory code", size=2, help="- Canadian province or territory in which the employee is located or the state in the USA where the employee is located\
    - use the abbreviations listed in the T619 - Electronic transmittal under section: Transmitter province or territory code\
    - when the employee's country code is neither CAN nor USA, enter ZZ in this field")
    employee_cntry_cd = fields.Char("Employee country code", size=3, help="- country in which the employee is located\
    - use the alphabetic country codes as outlined in the International Standard (ISO) 3166 Codes for the Representation of Names of Countries.\
    -  always use CAN for Canada, and USA for the United States of America.")
    employee_pstl_cd = fields.Char("Employee postal code", size=10, help="- employee's Canadian postal code, format: alpha, numeric, alpha, numeric, alpha, numeric, example: A9A9A9\
    - or the employee's USA zip code\
    - or where the employee's country code is neither CAN nor USA, enter the foreign postal code")
    employee_sin = fields.Char("Employee social insurance number (SIN)", help="- T4 slip, box 12\
    - When the employee has failed to provide a SIN, enter zeroes in the entire field.\
    Note: Omission of a valid SIN results in non-registration of contributions to the Canada Pension Plan.")
    employee_empe_nbr = fields.Char("Employee number", size=20,
                                    help="- for example: region and/or branch payroll and/or department and/or employee number")
    employee_bn = fields.Char("Payroll Account Number", size=15, help="- T4 slip, box 54\
    - must correspond to the 'Business Number (BN)' on the related T4 Summary record Note: To process a return, the complete BN is required")
    employee_rpp_dpsp_rgst_nbr = fields.Integer("RPP or DPSP registration number registration number", help="- T4 slip, box 50\
    - enter the registration number for the plan where the employee received the largest pension adjustment amount")
    employee_cpp_qpp_xmpt_cd = fields.Selection(selection=CODE,
                                                string="Canada Pension Plan or Quebec Pension Plan exempt code", help="- T4 slip, box 28\
    - 0 if no exemption applies or if the employee is exempt for a portion of the period\
    - 1 if the employee has been exempt from CPP or QPP for the entire period of employment due to age, nature of payment, etc.")
    employee_ei_xmpt_cd = fields.Selection(selection=CODE, string="Employment Insurance exempt code", help="- T4 slip, box 28\
    - 0 if no exemption applies or if the employee is exempt for a portion of the period\
    - 1 if the employee has been exempt from EI premiums for the entire period of employment due to age, nature of employment, etc.")
    employee_prov_pip_xmpt_cd = fields.Selection(selection=CODE, string="PPIP exempt code", help="- T4 slip, box 28\
    - 0 if no exemption applies\
    - 1 if the employee has been exempt")
    employee_empt_cd = fields.Selection(selection=EMPLOYMENT_CODE, string="Employment code", help="- T4 slip, box 29\
    - Do not complete Box 14 - Employment income, if you are using employment codes 11, 12, 13, or 17.\
    11 - Placement or employment agency workers\
    12 - Drivers of taxis or other passenger-carrying vehicles\
    13 - Barbers or hairdressers\
    14 - Withdrawal from a prescribed salary deferral arrangement plan\
    15 - Seasonal Agricultural Workers Program\
    16 - Detached employee - Social security agreement.\
    Note: When CPP is paid by the employer on behalf of detached employees under employment code 16, box 14 is left blank if no other type of income is reported. Boxes 16 and 26 are completed with the appropriate amounts and boxes 18 and 24 are left blank.\
    17 - Fishers - Self-employed")
    employee_rpt_tcd = fields.Selection(selection=REPORT_TYPE_CODE, string="Report Type Code", help="- originals = O\
    - amendments = A\
    - cancel = C\
    Note: An amended return cannot contain an original slip")
    employee_empt_prov_cd = fields.Selection(selection=PROVINCE_CODE,
                                             string="Province, territory or country of employment code", help="- T4 slip, box 10\
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
    employee_empt_incamt = fields.Float("Employment income", help="""-10 numeric
    - T4 slip, box 14
    Note: Do not complete box 14 if you are using employment codes 11, 12, 13, or 17. Refer to box 29 for these codes.""")

    employee_cpp_cntrb_amt = fields.Float("Employee's Canada Pension Plan (CPP) contributions", help=""""- 6 numeric
    - T4 slip, box 16
    Note: Under no circumstances should amounts for both CPP and QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_qpp_cntrb_amt = fields.Float("Employee's Quebec Pension Plan (QPP) contributions", help=""""- 6 numeric
    - T4 slip, box 17
    Note: Under no circumstances should amounts for both CPP and QPP appear on the same slip. A separate T4 slip is needed for each province of employment.""")

    employee_empe_eip_amt = fields.Float("Employee's Employment Insurance (EI) premium", help="""" 6 numeric
    - T4 slip, box 18""")

    registered_rpp_cntrb_amt = fields.Float("Registered pension plan (RPP) contributions", help="""" - 7 numeric
    - T4 slip, box 20""")

    income_itx_ddct_amt = fields.Float("Income tax deducted", help="""" - 10 numeric
    - T4 slip, box 22""")

    employee_ei_insu_ern_amt = fields.Float("Employment Insurance insurable earnings", help="""" - Required 7 numeric
    - T4 slip, box 24
    - enter "0.00" if there are no insurable earnings
    - for exempt employment, enter "0.00" """)

    canada_cpp_qpp_ern_amt = fields.Float("Canada Pension Plan or Quebec Pension Plan pensionable earnings", help="""- Required 9 numeric
    - T4 slip, box 26
    - if there are no pensionable earnings, enter "0.00"
    - for exempt employment, enter "0.00" """)

    union_unn_dues_amt = fields.Float("Union dues", help="""- 9 numeric
    - T4 slip, box 44 """)

    charitable_chrty_dons_amt = fields.Float("Charitable donations", help="""- 9 numeric
    - T4 slip, box 46 """)

    pension_padj_amt = fields.Float("Pension adjustment", help="""- 7 numeric
    - T4 slip, box 52""")

    PPIP_prov_pip_amt = fields.Float("PPIP Premiums", help="""- 6 Numeric
    - T4 Slip, box 55""")

    PPIP_prov_insu_ern_amt = fields.Float("PPIP Insurable earnings", help="""- 7 Numeric
    - T4 Slip, box 56""")

    # =================================== Other Info ===============================
    # hm_brd_lodg_amt
    hm_brd_lodg_amt = fields.Float("Housing, board and lodging amount", help="- Other Income Amount - Code 30")

    # spcl_wrk_site_amt
    spcl_wrk_site_amt = fields.Float("Special work site amount", help="- Other Income Amount - Code 31")

    # prscb_zn_trvl_amt
    prscb_zn_trvl_amt = fields.Float("Travel in a prescribed zone amount", help="- Other Income Amount - Code 32")

    # med_trvl_amt
    med_trvl_amt = fields.Float("Medical travel amount", help="- Other Income Amount - Code 33")

    # prsnl_vhcl_amt
    prsnl_vhcl_amt = fields.Float("Personal use of employer automobile amount", help="- Other Income Amount - Code 34")

    # rsn_per_km_amt
    rsn_per_km_amt = fields.Float("Total Reasonable Per-Kilometre Allowance amount",
                                  help="- Other Income amount - Code 35, applies to year 2000 and prior")

    # low_int_loan_amt
    low_int_loan_amt = fields.Float("Interest-free and low-interest loan amount",
                                    help="- Other Income Amount - Code 36")

    # empe_hm_loan_amt
    empe_hm_loan_amt = fields.Float("Employee home-relocation loan deduction amount",
                                    help="- Other Income Amount - Code 37")

    # stok_opt_ben_amt
    stok_opt_ben_amt = fields.Float("Stock option benefit amount before February 28, 2000",
                                    help="- Other Income Amount - Code 97, applies to year 2000 and prior")

    # sob_a00_feb_amt
    sob_a00_feb_amt = fields.Float("Security options benefits", help="- Other Income Amount - Code 38")

    # shr_opt_d_ben_amt
    shr_opt_d_ben_amt = fields.Float("Stock option and share deduction 110(1) (d) amount before February 28, 2000",
                                     help="- Other Income Amount - Code 98, applies to year 2000 and prior")

    # sod_d_a00_feb_amt
    sod_d_a00_feb_amt = fields.Float("Security options deductions 110(1)(d)", help="- Other Income Amount - Code 39")

    # oth_tx_ben_amt
    oth_tx_ben_amt = fields.Float("Other taxable allowance and benefit amount", help="- Other Income Amount - Code 40")

    # shr_opt_d1_ben_amt
    shr_opt_d1_ben_amt = fields.Float("Stock option and share deduction 110(1) (d.1) amount before February 28, 2000",
                                      help="- Other Income Amount - Code 99, applies to year 2000 and prior")

    # sod_d1_a00_feb_amt
    sod_d1_a00_feb_amt = fields.Float("Security options deduction 110(1)(d.1)",
                                      help="- Other Income Amount - Code 41\nNote: Do not include this amount in box 14.")

    # empt_cmsn_amt
    empt_cmsn_amt = fields.Float("Employment commission amount", help="- Other Income Amount - Code 42")

    # cfppa_amt
    cfppa_amt = fields.Float("Canadian armed forces personnel and police allowance",
                             help="- Other Income Amount - Code 43")

    # dfr_sob_amt
    dfr_sob_amt = fields.Float("Deferred security option benefits", help="- Other Income Amount - Code 53")

    # empt_inc_amt_covid_prd1
    empt_inc_amt_covid_prd1 = fields.Float("Employment income – March 15 to May 9 – 2020 tax year only",
                                           help="- Other Income Amount - Code 57")

    # empt_inc_amt_covid_prd2
    empt_inc_amt_covid_prd2 = fields.Float("Employment income – May 10 to July 4 – 2020 tax year only",
                                           help="- Other Income Amount - Code 58")

    # empt_inc_amt_covid_prd3
    empt_inc_amt_covid_prd3 = fields.Float("Employment income – July 5 to August 29 – 2020 tax year only",
                                           help="- Other Income Amount - Code 59")

    # empt_inc_amt_covid_prd4
    empt_inc_amt_covid_prd4 = fields.Float("Employment income – August 30 to September 26 – 2020 tax year only",
                                           help="- Other Income Amount - Code 60")

    # elg_rtir_amt
    elg_rtir_amt = fields.Float("Eligible retiring allowances",
                                help="- Other Income Amount – Code 66\n# Note: Do not include this amount in box 14.")

    # nelg_rtir_amt
    nelg_rtir_amt = fields.Float("Non-eligible retiring allowances",
                                 help="- Other Income Amount – Code 67\n# Note: Do not include this amount in box 14.")

    # indn_nelg_rtir_amt
    indn_nelg_rtir_amt = fields.Float("Status Indian Non-eligible retiring allowances",
                                      help="- Other Income Amount – Code 69\n# Note: Do not include this amount in box 14.")

    # indn_empe_amt
    indn_empe_amt = fields.Float("Status Indian employee amount",
                                 help="- Other Income Amount - Code 71\n# Note: If you are reporting this type of income, enter 0.00 in box 14.")

    # oc_incamt
    oc_incamt = fields.Float("Outside of Canada employment income amount- Section 122.3",
                             help="- Other Income Amount - Code 72")

    # oc_dy_cnt
    oc_dy_cnt = fields.Integer("Employment outside of Canada Day Count",
                               help="- 3 numeric\n- Other Income Field - Code 73")

    # pr_90_cntrbr_amt
    pr_90_cntrbr_amt = fields.Float("Pre-1990 past service contributions while a contributor",
                                    help="- Other Income Amount - Code 74")

    # pr_90_ncntrbr_amt
    pr_90_ncntrbr_amt = fields.Float("Pre-1990 past service contributions while not a contributor",
                                     help="- Other Income Amount - Code 75")

    # cmpn_rpay_empr_amt
    cmpn_rpay_empr_amt = fields.Float("Workers’ compensation benefit repaid to the employer amount",
                                      help="- Other Income Amount - Code 77\n# Note: Do not include this amount in box 14.")

    # fish_gro_ern_amt
    fish_gro_ern_amt = fields.Float("Fishers - Gross earnings",
                                    help="- Other Income Amount - Code 78\n# Note: Do not include this amount in box 14.")

    # fish_net_ptnr_amt
    fish_net_ptnr_amt = fields.Float("Fishers - Net Partnership Amount",
                                     help="- Other Income Amount - Code 79\n# Note: Do not include this amount in box 14.")

    # fish_shr_prsn_amt
    fish_shr_prsn_amt = fields.Float("Fishers - Shareperson Amount",
                                     help="- Other Income Amount - Code 80\n# Note: Do not include this amount in box 14.")

    # plcmt_emp_agcy_amt
    plcmt_emp_agcy_amt = fields.Float("Placement or employment agency",
                                      help="- Other Income Amount - Code 81\n# Note: Do not include this amount in box 14.")

    # drvr_taxis_oth_amt
    drvr_taxis_oth_amt = fields.Float("Driver of taxi or other passenger-carrying vehicle",
                                      help="- Other Income Amount - Code 82\nNote: Do not include this amount in box 14.")

    # brbr_hrdrssr_amt
    brbr_hrdrssr_amt = fields.Float("Barber or hairdresser",
                                    help="- Other Income Amount - Code 83\nNote: Do not include this amount in box 14.")

    # pub_trnst_pass_amt
    pub_trnst_pass_amt = fields.Float("Public transit pass", help="- Other Income Amount - Code 84")

    # epaid_hlth_pln_amt
    epaid_hlth_pln_amt = fields.Float("Employee-paid premiums for private health services plans",
                                      help="- Other Income Amount - Code 85\nNote: Do not include this amount in box 14.")

    # stok_opt_csh_out_eamt
    stok_opt_csh_out_eamt = fields.Float("Stock option cash-out expense", help="- Other Income Amount – Code 86")

    # vlntr_emergencyworker_xmpt_amt
    vlntr_emergencyworker_xmpt_amt = fields.Float("Emergency services volunteer exempt amount",
                                                  help="- Other Income Amount - Code 87\n- Valid for 2011 and subsequent tax years only\nNote: Do not include this amount in box 14.")

    # indn_txmpt_sei_amt
    indn_txmpt_sei_amt = fields.Float("Indian (exempt income) – Self-employment",
                                      help="- Other Income Amount - Code 88\nNote: Do not include this amount in box 14.")

    # ==================================== T4 Summary ===================================================
    # bn
    bn = fields.Char(
        string="Payroll Account Number",
        size=15,
        # required=True,
        help="- Required, 15 alphanumeric, 9 digits RP 4 digits, Example: 000000000RP0000"
    )

    # l1_nm
    employer_l1_nm = fields.Char(
        string="Employer name - line 1",
        size=30,
        # required=True,
        help="- Required 30 alphanumeric\n- first line of employer's name\n- if " '\n&' " is used in the name area enter as '&amp;'"
    )

    # l2_nm
    employer_l2_nm = fields.Char(
        string="Employer name - line 2",
        size=30,
        help="- 30 alphanumeric\n- Second line of employer's name"
    )

    # l3_nm
    employer_l3_nm = fields.Char(
        string="Employer name - line 3",
        size=30,
        help="- 30 alphanumeric\n- Use for 'care of' or 'attention'"
    )

    # addr_l1_txt
    employer_addr_l1_txt = fields.Char(
        string="Employer address - line 1",
        size=30,
        help="- 30 alphanumeric\n- First line of the employer's address"
    )

    # addr_l2_txt
    employer_addr_l2_txt = fields.Char(
        "Employer address - line 2",
        size=30,
        help="- 30 alphanumeric\n- Second line of the employer's address"
    )

    # cty_nm
    employer_cty_nm = fields.Char(
        "Employer city",
        size=28,
        help="- 28 alphanumeric\n- City in which the employer is located"
    )

    # prov_cd
    employer_prov_cd = fields.Char(
        "Employer province or territory code",
        size=2,
        help="- 2 alpha\n- Canadian province or territory in which the employer is located or the state in the USA where the employer is located. Use the abbreviations listed in the T619 - Electronic transmittal under section: Transmitter province or territory code. When the employer's country code is neither CAN nor USA, enter ZZ in this field."
    )

    # cntry_cd
    employer_cntry_cd = fields.Char(
        "Employer country code",
        size=3,
        help="- 3 alpha\n- Country in which the employer is located. Use the alphabetic country codes as outlined in the International Standard (ISO) 3166 Codes for the Representation of Names of Countries. Always use CAN for Canada, and USA for the United States of America."
    )

    # pstl_cd
    employer_pstl_cd = fields.Char("- 10 alphanumeric\n- Employer postal code", size=10,
                                   help="Employer's Canadian postal code (format: alpha, numeric, alpha, numeric, alpha, numeric, example: A9A9A9) or the employer's USA zip code. When the employer's country code is neither CAN nor USA, enter the foreign postal code.")

    # cntc_nm
    cntc_nm = fields.Char(
        "Contact name",
        size=22,
        # required=True,
        help="- Required, 22 alphanumeric\n- Contact's first name followed by surname for this return. Omit titles such as Mr., Mrs., etc."
    )

    # cntc_area_cd
    cntc_area_cd = fields.Char(
        "Contact area code",
        size=3,
        # required=True,
        help="- Required, 3 numeric\n- Area code of telephone number."
    )

    # cntc_phn_nbr
    cntc_phn_nbr = fields.Char(
        "Contact telephone number",
        size=8,
        # required=True,
        help="- Required, 3 numeric with a (-), followed by 4 numeric.\n- Telephone number of the contact (format: ###-####)."
    )

    # cntc_extn_nbr
    cntc_extn_nbr = fields.Char(
        "Contact extension",
        size=5,
        help="- 5 numeric\n- Extension of the contact."
    )

    # tx_yr
    tx_yr = fields.Char(
        "Taxation year",
        size=4,
        # required=True,
        help="- Required, 4 numeric\n- Taxation year (e.g., 2001)."
    )

    # slp_cnt
    slp_cnt = fields.Char(
        "Total number of T4 slip records",
        size=7,
        # required=True,
        help="- Required, 7 numeric\n- Total number of T4 slip records filed with this T4 Summary."
    )

    # pprtr_1_sin
    pprtr_1_sin = fields.Char(
        "Proprietor #1 social insurance number (SIN)",
        size=9,
        # required=True,
        help="- Required, 9 numeric\n- If the employer is a Canadian-controlled private corporation or unincorporated, enter the SIN of the proprietor #1 or principal owner."
    )

    # pprtr_2_sin
    pprtr_2_sin = fields.Char(
        "Proprietor #2 social insurance number (SIN)",
        size=9,
        help="- 9 numeric\n- If the employer is a Canadian-controlled private corporation or unincorporated, enter the SIN of the proprietor #2 or second principal owner."
    )

    # rpt_tcd
    rpt_tcd = fields.Selection(
        [("O", "Originals"), ("A", "Amendments")],
        string="Report Type Code",
        # required=True,
        help="- Required, 1 alpha\n- Originals = O\n- Amendments = A\n-Note: An amended return cannot contain an original slip."
    )

    # fileramendmentnote
    fileramendmentnote = fields.Char(
        "Filer amendment note",
        size=1309,
        help="Use for report type A only.\n- 1309 alphanumeric"
    )

    # tot_empt_incamt
    tot_empt_incamt = fields.Float(
        string="Total employment income",
        help="- 13 numeric\n- Accumulated total of employees' income"
    )

    # tot_empe_cpp_amt
    tot_empe_cpp_amt = fields.Float(
        string="Total employees' Canada Pension Plan contributions",
        help="- 11 numeric\n- Accumulated total of employees' Canada Pension Plan contributions"
    )

    # tot_empe_eip_amt
    tot_empe_eip_amt = fields.Float(
        string="Total employees' employment insurance premiums",
        help="- 11 numeric\n- Accumulated total of employees' Employment Insurance premiums"
    )

    # tot_rpp_cntrb_amt
    tot_rpp_cntrb_amt = fields.Float(
        string="Total registered pension plan contributions",
        help="- 11 numeric\n- Accumulated total of employees' registered pension plan contributions"
    )

    # tot_itx_ddct_amt
    tot_itx_ddct_amt = fields.Float(
        string="Total income tax deducted",
        help="- 13 numeric\n- Accumulated total of employees' income tax deductions"
    )

    # tot_padj_amt
    tot_padj_amt = fields.Float(
        string="Total pension adjustment",
        help="- 13 numeric\n- Accumulated total of employees' pension adjustment"
    )

    # tot_empr_cpp_amt
    tot_empr_cpp_amt = fields.Float(
        string="Total employer's Canada Pension Plan contributions", help="- 11 numeric"
    )

    # tot_empr_eip_amt
    tot_empr_eip_amt = fields.Float(
        string="Total employer's Employment Insurance premiums", help="- 11 numeric"
    )


    def open_t4_website(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.canada.ca/en/revenue-agency/services/e-services/e-services-businesses/business-account.html',
            'target': 'new',
        }

    @api.onchange('employee_id')
    def _onchage_contract_ids(self):
        contract_domain_ids = self.env['hr.contract'].search([
            ('company_id', '=', self.company_id.id),
            ('employee_id', '=', self.employee_id.id),
            ('state', '!=', 'cancel'),
            # ('date_start', '<=', payslip.date_to),
            # '|',
            # ('date_end', '>=', payslip.date_from),
            # ('date_end', '=', False)
        ])
        return {'domain': {'employee_contract': [('id', 'in', contract_domain_ids.ids)]}}
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

        employee_contract = self.employee_contract
        t4_amount = {}
        cpp_cnt_amount = 0.0
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

        for pay in year_specific_employee_payslip_ids:
            for line in pay.line_ids:
                # if line.code == 'CPP_QPP_EA':
                #     canada_cpp_qpp_ern_amt += line.amount
                if line.code == 'CPP':
                    cpp_cnt_amount += line.amount
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

            # if
            # cpp_cnt_amount +=

        t4_amount.update({
            'employee_empt_incamt': round(employee_empt_incamt,2),
            'tot_empt_incamt': round(employee_empt_incamt,2),
            'income_itx_ddct_amt': round(income_itx_ddct_amt,2),
            'tot_itx_ddct_amt': round(income_itx_ddct_amt,2),
            'union_unn_dues_amt': round(union_unn_dues_amt,2),
            'charitable_chrty_dons_amt': round(charitable_chrty_dons_amt,2),
            'pension_padj_amt': round(pension_padj_amt,2),
        })
        if not employee_contract.is_cpp_qpp_xmpt_cd:
            canada_cpp_qpp_ern_amt = round(employee_empt_incamt, 2)
            t4_amount.update(
                {'employee_cpp_cntrb_amt': round(cpp_cnt_amount,2),
                 'tot_empe_cpp_amt': round(cpp_cnt_amount,2),
                 'tot_empr_cpp_amt': round(cpp_cnt_amount,2),
                 'canada_cpp_qpp_ern_amt': round(canada_cpp_qpp_ern_amt,2)}
            )
        if not employee_contract.is_ei_xmpt_cd:
            employee_ei_insu_ern_amt = round(employee_empt_incamt, 2)
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
                # "cntc_phn_nbr": employeer_contact_id.phone or '',
                "slp_cnt": '1',
                "tx_yr": self.year,
                "pprtr_1_sin": str(employeer.employeer_pprtr_1_sin) or "",
                "pprtr_2_sin": str(employeer.employeer_pprtr_2_sin) or "",
                "rpt_tcd": self.employee_rpt_tcd if self.employee_rpt_tcd == 'A' else None,

            })

            self.write(payload)

        # return None

    # ======================== Generate and download T4 xml ===========================
    def download_t4_xml(self):
        # Generate the T4 XML content
        kwrgs=[]
        for rec in self:
            xml_content = rec.generate_t4_xml()
            rec.xml_content = xml_content

            # Prepare the file for download
            filename = f'{rec.employee_id.name}' + '_T4' + '.xml'
            content_type = 'application/xml'

            kwrgs.append((rec.id,filename, content_type))

        # Return the file as a response
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=statement.remuneration&field=xml_content&id=%s&filename=%s&content_type=%s' % (
                    rec.id, filename, content_type),
                'target': 'self',
            }

    def create_t4_xml(self):
        # Create the root element
        root = ET.Element("Return")

        # Create the T4 element
        t4 = ET.SubElement(root, "T4")

        # Create the T4Slip element
        t4_slip = ET.SubElement(t4, "T4Slip")

        # Add EMPE_NM subelement
        empe_nm = ET.SubElement(t4_slip, "EMPE_NM")
        ET.SubElement(empe_nm, "snm").text = self.employee_snm
        ET.SubElement(empe_nm, "gvn_nm").text = self.employee_gvn_nm
        ET.SubElement(empe_nm, "init").text = self.employee_init

        # Add EMPE_ADDR subelement
        empe_addr = ET.SubElement(t4_slip, "EMPE_ADDR")
        ET.SubElement(empe_addr, "addr_l1_txt").text = self.employee_addr_l1_txt
        ET.SubElement(empe_addr, "addr_l2_txt").text = self.employee_addr_l2_txt
        ET.SubElement(empe_addr, "cty_nm").text = self.employee_cty_nm
        ET.SubElement(empe_addr, "prov_cd").text = self.employee_prov_cd
        ET.SubElement(empe_addr, "cntry_cd").text = self.employee_cntry_cd
        ET.SubElement(empe_addr, "pstl_cd").text = self.employee_pstl_cd

        # Add other subelements
        ET.SubElement(t4_slip, "sin").text = str(self.employee_sin)
        ET.SubElement(t4_slip, "empe_nbr").text = str(self.employee_empe_nbr) or ''
        ET.SubElement(t4_slip, "bn").text = str(self.employee_bn) or ''
        ET.SubElement(t4_slip, "rpp_dpsp_rgst_nbr").text = str(self.employee_rpp_dpsp_rgst_nbr) or ''
        ET.SubElement(t4_slip, "cpp_qpp_xmpt_cd").text = str(self.employee_cpp_qpp_xmpt_cd) or ''
        ET.SubElement(t4_slip, "ei_xmpt_cd").text = str(self.employee_ei_xmpt_cd) or ''
        ET.SubElement(t4_slip, "prov_pip_xmpt_cd").text = str(self.employee_prov_pip_xmpt_cd) or ''
        ET.SubElement(t4_slip, "empt_cd").text = str(self.employee_empt_cd) or ''
        ET.SubElement(t4_slip, "rpt_tcd").text = str(self.employee_rpt_tcd) or ''
        ET.SubElement(t4_slip, "empt_prov_cd").text = str(self.employee_empt_prov_cd) or ''

        # Add T4_AMT subelement
        t4_amt = ET.SubElement(t4_slip, "T4_AMT")
        ET.SubElement(t4_amt, "empt_incamt").text = str(self.employee_empt_incamt) or ''
        ET.SubElement(t4_amt, "cpp_cntrb_amt").text = str(self.employee_cpp_cntrb_amt) or ''
        ET.SubElement(t4_amt, "qpp_cntrb_amt").text = str(self.employee_qpp_cntrb_amt) or ''
        ET.SubElement(t4_amt, "empe_eip_amt").text = str(self.employee_empe_eip_amt) or ''
        ET.SubElement(t4_amt, "rpp_cntrb_amt").text = str(self.registered_rpp_cntrb_amt) or ''
        ET.SubElement(t4_amt, "itx_ddct_amt").text = str(self.income_itx_ddct_amt) or ''
        ET.SubElement(t4_amt, "ei_insu_ern_amt").text = str(self.employee_ei_insu_ern_amt) or ''
        ET.SubElement(t4_amt, "cpp_qpp_ern_amt").text = str(self.canada_cpp_qpp_ern_amt) or ''
        ET.SubElement(t4_amt, "unn_dues_amt").text = str(self.union_unn_dues_amt) or ''
        ET.SubElement(t4_amt, "chrty_dons_amt").text = str(self.charitable_chrty_dons_amt) or ''
        ET.SubElement(t4_amt, "padj_amt").text = str(self.pension_padj_amt) or ''
        ET.SubElement(t4_amt, "prov_pip_amt").text = str(self.PPIP_prov_pip_amt) or ''
        ET.SubElement(t4_amt, "prov_insu_ern_amt").text = str(self.PPIP_prov_insu_ern_amt) or ''

        # Add OTH_INFO subelement
        oth_info = ET.SubElement(t4_slip, "OTH_INFO")
        ET.SubElement(oth_info, "hm_brd_lodg_amt").text = str(self.hm_brd_lodg_amt) or ''
        ET.SubElement(oth_info, "spcl_wrk_site_amt").text = str(self.spcl_wrk_site_amt) or ''
        ET.SubElement(oth_info, "prscb_zn_trvl_amt").text = str(self.prscb_zn_trvl_amt) or ''
        ET.SubElement(oth_info, "med_trvl_amt").text = str(self.med_trvl_amt) or ''
        ET.SubElement(oth_info, "prsnl_vhcl_amt").text = str(self.prsnl_vhcl_amt) or ''
        ET.SubElement(oth_info, "rsn_per_km_amt").text = str(self.rsn_per_km_amt) or ''
        ET.SubElement(oth_info, "low_int_loan_amt").text = str(self.low_int_loan_amt) or ''
        ET.SubElement(oth_info, "empe_hm_loan_amt").text = str(self.empe_hm_loan_amt) or ''
        ET.SubElement(oth_info, "stok_opt_ben_amt").text = str(self.stok_opt_ben_amt) or ''
        ET.SubElement(oth_info, "sob_a00_feb_amt").text = str(self.sob_a00_feb_amt) or ''
        ET.SubElement(oth_info, "shr_opt_d_ben_amt").text = str(self.shr_opt_d_ben_amt) or ''
        ET.SubElement(oth_info, "sod_d_a00_feb_amt").text = str(self.sod_d_a00_feb_amt) or ''
        ET.SubElement(oth_info, "oth_tx_ben_amt").text = str(self.oth_tx_ben_amt) or ''
        ET.SubElement(oth_info, "shr_opt_d1_ben_amt").text = str(self.shr_opt_d1_ben_amt) or ''
        ET.SubElement(oth_info, "sod_d1_a00_feb_amt").text = str(self.sod_d1_a00_feb_amt) or ''
        ET.SubElement(oth_info, "empt_cmsn_amt").text = str(self.empt_cmsn_amt) or ''
        ET.SubElement(oth_info, "cfppa_amt").text = str(self.cfppa_amt) or ''
        ET.SubElement(oth_info, "dfr_sob_amt").text = str(self.dfr_sob_amt) or ''
        ET.SubElement(oth_info, "empt_inc_amt_covid_prd1").text = str(self.empt_inc_amt_covid_prd1) or ''
        ET.SubElement(oth_info, "empt_inc_amt_covid_prd2").text = str(self.empt_inc_amt_covid_prd2) or ''
        ET.SubElement(oth_info, "empt_inc_amt_covid_prd3").text = str(self.empt_inc_amt_covid_prd3) or ''
        ET.SubElement(oth_info, "empt_inc_amt_covid_prd4").text = str(self.empt_inc_amt_covid_prd4) or ''
        ET.SubElement(oth_info, "elg_rtir_amt").text = str(self.nelg_rtir_amt) or ''
        ET.SubElement(oth_info, "nelg_rtir_amt").text = str(self.indn_nelg_rtir_amt) or ''
        ET.SubElement(oth_info, "indn_nelg_rtir_amt").text = str(self.indn_nelg_rtir_amt) or ''
        ET.SubElement(oth_info, "indn_empe_amt").text = str(self.indn_empe_amt) or ''
        ET.SubElement(oth_info, "oc_incamt").text = str(self.oc_incamt) or ''
        ET.SubElement(oth_info, "oc_dy_cnt").text = str(self.oc_dy_cnt) or ''
        ET.SubElement(oth_info, "pr_90_cntrbr_amt").text = str(self.pr_90_cntrbr_amt) or ''
        ET.SubElement(oth_info, "pr_90_ncntrbr_amt").text = str(self.pr_90_ncntrbr_amt) or ''
        ET.SubElement(oth_info, "cmpn_rpay_empr_amt").text = str(self.cmpn_rpay_empr_amt) or ''
        ET.SubElement(oth_info, "fish_gro_ern_amt").text = str(self.fish_gro_ern_amt) or ''
        ET.SubElement(oth_info, "fish_net_ptnr_amt").text = str(self.fish_net_ptnr_amt) or ''
        ET.SubElement(oth_info, "fish_shr_prsn_amt").text = str(self.fish_shr_prsn_amt) or ''
        ET.SubElement(oth_info, "plcmt_emp_agcy_amt").text = str(self.plcmt_emp_agcy_amt) or ''
        ET.SubElement(oth_info, "drvr_taxis_oth_amt").text = str(self.drvr_taxis_oth_amt) or ''
        ET.SubElement(oth_info, "brbr_hrdrssr_amt").text = str(self.brbr_hrdrssr_amt) or ''
        ET.SubElement(oth_info, "pub_trnst_pass_amt").text = str(self.pub_trnst_pass_amt) or ''
        ET.SubElement(oth_info, "epaid_hlth_pln_amt").text = str(self.epaid_hlth_pln_amt) or ''
        ET.SubElement(oth_info, "stok_opt_csh_out_eamt").text = str(self.stok_opt_csh_out_eamt) or ''
        ET.SubElement(oth_info, "vlntr_emergencyworker_xmpt_amt").text = str(self.vlntr_emergencyworker_xmpt_amt) or ''
        ET.SubElement(oth_info, "indn_txmpt_sei_amt").text = str(self.indn_txmpt_sei_amt) or ''

        # Create T4Summary element
        t4_summary = ET.SubElement(t4, "T4Summary")
        ET.SubElement(t4_summary, "bn").text = str(self.bn) or ''

        # Add EMPR_NM subelement
        empr_nm = ET.SubElement(t4_summary, "EMPR_NM")
        ET.SubElement(empr_nm, "l1_nm").text = str(self.employer_l1_nm) or ''
        ET.SubElement(empr_nm, "l2_nm").text = str(self.employer_l2_nm) or ''
        ET.SubElement(empr_nm, "l3_nm").text = str(self.employer_l3_nm) or ''

        # Add EMPR_ADDR subelement
        empr_addr = ET.SubElement(t4_summary, "EMPR_ADDR")
        ET.SubElement(empr_addr, "addr_l1_txt").text = str(self.employer_addr_l1_txt) or ''
        ET.SubElement(empr_addr, "addr_l2_txt").text = str(self.employer_addr_l2_txt) or ''
        ET.SubElement(empr_addr, "cty_nm").text = str(self.employer_cty_nm) or ''
        ET.SubElement(empr_addr, "prov_cd").text = str(self.employer_prov_cd) or ''
        ET.SubElement(empr_addr, "cntry_cd").text = str(self.employer_cntry_cd) or ''
        ET.SubElement(empr_addr, "pstl_cd").text = str(self.employer_pstl_cd) or ''

        # Add CNTC subelement
        cntc = ET.SubElement(t4_summary, "CNTC")
        ET.SubElement(cntc, "cntc_nm").text = str(self.cntc_nm) or ''
        ET.SubElement(cntc, "cntc_area_cd").text = str(self.cntc_area_cd) or ''
        ET.SubElement(cntc, "cntc_phn_nbr").text = str(self.cntc_phn_nbr) or ''
        ET.SubElement(cntc, "cntc_extn_nbr").text = str(self.cntc_extn_nbr) or ''

        ET.SubElement(t4_summary, "tx_yr").text = str(self.tx_yr) or ''
        ET.SubElement(t4_summary, "slp_cnt").text = str(self.slp_cnt) or ''

        # Add PPRTR_SIN subelement
        pprtr_sin = ET.SubElement(t4_summary, "PPRTR_SIN")
        ET.SubElement(pprtr_sin, "pprtr_1_sin").text = str(self.pprtr_1_sin) or ''
        ET.SubElement(pprtr_sin, "pprtr_2_sin").text = str(self.pprtr_2_sin) or ''

        ET.SubElement(t4_summary, "rpt_tcd").text = str(self.rpt_tcd) or ''
        ET.SubElement(t4_summary, "fileramendmentnote").text = str(self.fileramendmentnote) or ''

        # Add T4_TAMT subelement
        t4_tamt = ET.SubElement(t4_summary, "T4_TAMT")
        ET.SubElement(t4_tamt, "tot_empt_incamt").text = str(self.tot_empt_incamt) or ''
        ET.SubElement(t4_tamt, "tot_empe_cpp_amt").text = str(self.tot_empe_cpp_amt) or ''
        ET.SubElement(t4_tamt, "tot_empe_eip_amt").text = str(self.tot_empe_eip_amt) or ''
        ET.SubElement(t4_tamt, "tot_rpp_cntrb_amt").text = str(self.tot_rpp_cntrb_amt) or ''
        ET.SubElement(t4_tamt, "tot_itx_ddct_amt").text = str(self.tot_itx_ddct_amt) or ''
        # ET.SubElement(t4_tamt, "tot_ei_insu_ern_amt").text = "2000.00"
        # ET.SubElement(t4_tamt, "tot_cpp_qpp_ern_amt").text = "3000.00"
        # ET.SubElement(t4_tamt, "tot_unn_dues_amt").text = "100.00"
        # ET.SubElement(t4_tamt, "tot_chrty_dons_amt").text = "200.00"
        ET.SubElement(t4_tamt, "tot_padj_amt").text = str(self.tot_padj_amt) or ''
        ET.SubElement(t4_tamt, "tot_empr_cpp_amt").text = str(self.tot_empr_cpp_amt) or ''
        ET.SubElement(t4_tamt, "tot_empr_eip_amt").text = str(self.tot_empr_eip_amt) or ''
        # ET.SubElement(t4_tamt, "tot_prov_pip_amt").text = "100.00"
        # ET.SubElement(t4_tamt, "tot_prov_insu_ern_amt").text = "1000.00"

        # Create the XML tree
        tree = ET.ElementTree(root)

        # Convert the XML tree to a string
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)

        # Return the XML string
        return xml_str.decode()

    def generate_t4_xml(self):
        # Call the function you created in step 2 to generate the T4 XML content
        xml_content = self.create_t4_xml()
        return xml_content

    # ======================== Generate and download T4 PDF ===========================
    def download_t4_pdf(self, is_bulk=False):
        kwrgs=[]
        for rec in self:
            if rec.state == 'done':
                try:
                    get_path = get_module_resource('syncoria_can_payroll', 'utils')
                    output_folder_path = os.path.expanduser(os.getenv("HOME")) + "/outPdf/"
                    if not os.path.isdir(output_folder_path):
                        os.mkdir(output_folder_path)
                    if is_bulk:  # Change the PDF name if called from the action
                        pdf_name = "Merged_T4.pdf"
                    else:
                        pdf_name = str(
                            datetime.datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-{rec.year}-")) + str(
                            datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".pdf"
                    filename = output_folder_path + pdf_name

                    reader = PdfReader(get_path + '/' + "t4-fill-22e.pdf")
                    writer = PdfWriter()

                    page = reader.pages[0]
                    fields = reader.get_fields()

                    writer.append(reader)

                    data = {'Slip1Year[0]': rec.year,
                            'Slip1EmployersName[0]': f'{rec.employer_l1_nm}\n{rec.employer_addr_l1_txt}\n{rec.employer_cty_nm},{rec.employer_prov_cd} {rec.employer_pstl_cd}',
                            'Slip1Box54[0]': None,
                            'Slip1Box12[0]': rec.employee_sin, 'Slip1Box14[0]': round(rec.employee_empt_incamt,2),
                            'Slip1Box22[0]': round(rec.income_itx_ddct_amt, 2), 'Slip1Box10[0]': 'ON',
                            'Slip1Box16[0]': round(rec.employee_cpp_cntrb_amt,2),
                            'Slip1Box24[0]': round(rec.employee_ei_insu_ern_amt,2), 'Slip1Box17[0]': 0.0,
                            'Slip1Box26[0]': round(rec.canada_cpp_qpp_ern_amt,2), 'Slip1Box18[0]': rec.employee_empe_eip_amt,
                            'Slip1Box44[0]': rec.union_unn_dues_amt, 'Slip1Box20[0]': 0.0,
                            'Slip1Box46[0]': rec.charitable_chrty_dons_amt, 'Slip1Box52[0]': rec.pension_padj_amt,
                            'Slip1Box50[0]': rec.employee_rpp_dpsp_rgst_nbr, 'Slip1Box55[0]': rec.PPIP_prov_pip_amt,
                            'Slip1Box56[0]': rec.PPIP_prov_insu_ern_amt, 'Slip1LastName[0]': rec.employee_snm,
                            'Slip1FirstName[0]': rec.employee_gvn_nm, 'Slip1Initial[0]': rec.employee_init,
                            'Slip1Address[0]': f'{rec.employee_addr_l1_txt}\n{rec.employee_addr_l2_txt}\n{rec.employee_cty_nm}\n{rec.employee_prov_cd} {rec.employee_pstl_cd}',
                            'Slip1Amount1[0]': None,
                            'Slip1Amount2[0]': None, 'Slip1Amount3[0]': None, 'Slip1Amount4[0]': None, 'Slip1Amount5[0]': None,
                            'Slip1Amount6[0]': None, 'Slip1EmployersName[0].2': None,
                            'Slip1Year[0].2': None, 'Slip1Box54[0].2': None, 'Slip1Box12[0].2': None, 'Slip1Box14[0].2': None,
                            'Slip1Box22[0].2': None, 'Slip1Box16[0].2': None, 'Slip1Box24[0].2': None, 'Slip1Box17[0].2': None,
                            'Slip1Box26[0].2': None, 'Slip1Box18[0].2': None, 'Slip1Box44[0].2': None, 'Slip1Box20[0].2': None,
                            'Slip1Box46[0].2': None, 'Slip1Box52[0].2': None, 'Slip1Box50[0].2': None, 'Slip1Box55[0].2': None,
                            'Slip1Box56[0].2': None, 'Slip1LastName[0].2': None, 'Slip1FirstName[0].2': None,
                            'Slip1Initial[0].2': None, 'Slip1Address[0].2': None, 'Slip1Amount1[0].2': None,
                            'Slip1Amount2[0].2': None, 'Slip1Amount3[0].2': None, 'Slip1Amount4[0].2': None,
                            'Slip1Amount5[0].2': None, 'Slip1Amount6[0].2': None}

                    writer.update_page_form_field_values(writer.pages[0], data)

                    # write "output" to pypdf-output.pdf
                    with open(filename, "wb") as output_stream:
                        writer.write(output_stream)
                except PermissionError as pe:
                    raise UserError(_(f"Permission Error:{pe}"))
                except IOError as ie:
                    raise UserError(_(f'IO Error:{ie}'))
                except Exception as e:
                    raise UserError(_(f"Internal Error:{e}"))

                kwrgs.append((filename, pdf_name))

        return {
            'type': 'ir.actions.act_url',
            'url': '/download/pdf?file_path=%s&file_name=%s&file_paths=%s' % ('', pdf_name,kwrgs),
            'target': 'new',
        }

    def send_t4_xml_batch(self):
        files_list=[]
        mail_template = self.env.ref('syncoria_can_payroll.email_template_batch_xml')
        for rec in self:
            xml_content = rec.generate_t4_xml()
            rec.xml_content = xml_content

            attachment = self.env['ir.attachment'].create({
                'name': str(
                        datetime.datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-{rec.year}-")) + str(
                        datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".xml",
                'raw': xml_content,
                'res_id': rec.id,
                'res_model': 'statement.remuneration',
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            files_list.append((4, attachment.id))

        # mail_template.attachment_ids = files_list
        email_values = {
            "attachment_ids": files_list
        }

        try:
            mail_template.send_mail(rec.id, force_send=True, raise_exception=True,email_values=email_values)
            message = "Your email has been sent."
            notification_type = 'success'
        except Exception as e:
            message = f"Error occurred while sending email: {str(e)}"
            notification_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': notification_type,
                'sticky': True,
            }
        }


