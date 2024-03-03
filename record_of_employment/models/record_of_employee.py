from odoo import fields, models, api, _
import os
import xml.etree.ElementTree as ET
from lxml import etree
from odoo.exceptions import UserError

from odoo.modules.module import get_module_resource
import datetime

from pypdf import PdfReader, PdfWriter

PAY_PERIOD = [
    ("weekly", "W - Weekly"),
    ("bi_weekly", "B - Bi-Weekly"),
    ("semi_monthly", "S - Semi-Monthly"),
    ("monthly", "M - Monthly"),
]

REASON_FOR_ROE = [
    ("shortage_of_work", "00-Shortage of work / End of contract or season"),
    ("retirement", "G07-Retirement / Approved workforce reduction"),
    ("employer_bankruptcy_or_receivership", "A01-Employer bankruptcy or receivership"),
    ("work_sharing", "H00-Work-Sharing"),
    ("strike_or_lockout", "B00-Strike or lockout"),
    ("apprentice_training", "J00-Apprentice training"),
    ("dismissal", "M00-Dismissal"),
    ("dismissal_termination_within_probation", "M08-Dismissal / Terminated within probationary period"),
    ("leave_of_absence", "N00-Leave of absence"),
    ("maternity", "F00-Maternity"),
    ("parental", "P00-Parental"),
    ("mandatory_retirement", "G00-Mandatory retirement"),
    ("compassionate_care", "Z00-Compassionate Care"),
    ("quit_shortage_of_work", "E00-Quit"),
    ("quit_follow_spouse", "E02-Quit / Follow spouse"),
    ("quit_return_to_school", "E03-Quit / Return to school"),
    ("quit_health_reasons", "E04-Quit / Health reasons"),
    ("quit_voluntary_retirement", "E05-Quit / Voluntary retirement"),
    ("quit_take_another_job", "E06-Quit / Take another job"),
    ("quit_employer_relocation", "E09-Quit / Employer relocation"),
    ("quit_care_for_dependant", "E10-Quit / Care for a dependant"),
    ("quit_become_self_employed", "E11-Quit / To become self-employed"),
    ("other_change_of_payroll_frequency", "K12-Other / Change of payroll frequency"),
    ("other_change_of_ownership", "K13-Other / Change of ownership"),
    ("other_requested_by_employment_insurance", "K14-Other / Requested by Employment Insurance"),
    ("other_canadian_forces_queen_regulations_orders", "K15-Other / Canadian Forces - Queen's Regulations / Orders"),
    ("other_at_employee_request", "K16-Other / At the employee's request"),
    ("other_change_of_service_provider", "K17-Other / Change of Service Provider"),
]


class RecordOfEmployee(models.Model):
    _name = "record.of.employee"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Record of Employee"
    # _rec_name = ""

    xml_content = fields.Text(string='XML Content')
    employee_id = fields.Many2one("hr.employee", string="9-Employee")
    company_id = fields.Many2one("res.company", string="Company")
    state = fields.Selection([
        ('draft', 'New'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
        tracking=True, help='Status of the ROE form', default='draft')

    # =======================================================================
    serial_no = fields.Char(string="1-Serial No.")
    amended_serial_no = fields.Char(string="2-Serial No Of ROE Amended Or Replaced")
    employer_payroll_ref = fields.Char(string="3-Employer's Payroll Reference Number")
    cra_payroll_acc_num = fields.Char(string="5-CRA Payroll Account Number")
    pay_period_id = fields.Many2one("paycycle.config", string="6-Pay Period Type")
    """ Need to Implement """
    expected_date_of_recall = fields.Selection([("not_returning", "N-Not Returning"), ("unknown", "U-Unknown"),
                                                ("expected_date_recall", "Y-Expected Date Of Recall")],
                                               default="not_returning", string="14.Expected Date Of Recall")
    # is_returning = fields.Boolean(string="Is Returning?")
    social_insurance_number = fields.Char(string="8-Social Insurance Number")
    first_day_worked = fields.Date(string="10-First Day Worked")
    last_day_worked = fields.Date(string="11-Last Day Worked")
    final_pay_period_ending_date = fields.Date(string="12-Final Pay Period Ending Date")
    occupation = fields.Char(string="13-Occupation")
    total_insurable_hours = fields.Float(string="15a-Total Insurable Hour According To Chart")
    total_insurable_earnings = fields.Float(string="15b-Total Insurable Earnings According To Chart")
    reason_for_issuing_roe = fields.Selection(REASON_FOR_ROE, string="16-Reason For Issuing This ROE",
                                              default='quit_take_another_job')
    vacation_pay_amount = fields.Char(string="17a-Vacation Pay")
    vacation_pay_start_date = fields.Date(string="Start Date")
    vacation_pay_end_date = fields.Date(string="End Date")
    statutory_holiday_pay_amount = fields.Char(string="17b-Statutory Holiday Pay")
    comments = fields.Char(string="18-Comments")
    language = fields.Selection([("english", "English"), ("french", "French")], default="english",
                                string="20-Communication Preferred In")
    telephone_no = fields.Char(string="21-Telephone No", unaccent=False)
    name_of_issuer_id = fields.Many2one("hr.employee", string="22-Name of Issuer")
    payslip_ids = fields.One2many("hr.payslip", "roe_id", string="15c-PaySlip")
    vacation_pay_ids = fields.One2many("hr.vacation.pay", "roe_id", string="Vacation Pay")

    issuing_date = fields.Date.today()

    _sql_constraints = [
        ('employee_id', 'unique(employee_id)', "ROE already exist!"),
    ]

    def _compute_display_name(self):
        for rec in self:
            if rec.employee_id.name:
                rec.display_name = f"{rec.employee_id.name}"
            else:
                super()._compute_display_name()

    def open_roe_website(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.canada.ca/en/employment-social-development/programs/ei/ei-list/ei-roe/access-roe.html',
            'target': 'new',
        }

    def get_payslip_ids(self):
        employee_payslip_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ("state", "=", "paid")]).sorted(reverse=True,
                                                                                        key=lambda x: x.date_to)
        return employee_payslip_ids

    def get_vacation_pay_ids(self):
        employee_vacation_pay_ids = self.env['hr.vacation.pay'].search(
            [('employee_id', '=', self.employee_id.id), ("state", "=", "paid")]).sorted(reverse=True,
                                                                                        key=lambda x: x.paid_date)
        return employee_vacation_pay_ids

    def _get_insurable_earning(self):
        employee_payslip_ids = self.get_payslip_ids()

        total_insurable_earning = 0.0

        for line in employee_payslip_ids.line_ids:
            if line.code == "I_Earning":
                total_insurable_earning += line.amount

        return total_insurable_earning

    def _get_insurable_hour(self):
        employee_payslip_ids = self.get_payslip_ids()

        total_insurable_hour = 0.0

        for line in employee_payslip_ids:
            total_insurable_hour += line.insurable_hour

        return total_insurable_hour

    def compute_roe(self):
        if self.employee_id:
            employee = self.employee_id
            payslip_ids = self.get_payslip_ids()
            has_last_payment = self.vacation_pay_ids.filtered(lambda x: x.is_last_pay)

            self.write({
                "company_id": employee.company_id,
                "pay_period_id": employee.contract_id.salary_pay_cycle,
                "social_insurance_number": employee.identification_id,
                "first_day_worked": employee.contract_id.date_start,
                "last_day_worked": employee.contract_id.date_end,
                "final_pay_period_ending_date": payslip_ids[0].date_to if payslip_ids else '',
                "occupation": employee.job_id.name,
                "cra_payroll_acc_num": employee.registration_number,
                "employer_payroll_ref": self.name_of_issuer_id.registration_number or '',
                "total_insurable_hours": self._get_insurable_hour(),
                "total_insurable_earnings": self._get_insurable_earning(),
                "payslip_ids": payslip_ids,
                "vacation_pay_ids": self.get_vacation_pay_ids(),
                "vacation_pay_amount": round(has_last_payment[0].vacation_pay_amount,2) if has_last_payment else ''
            })

        # ======================== Generate and download T4 xml ===========================

    def download_roe_xml(self):
        # Generate the T4 XML content

        xml_content = self.generate_roe_xml()

        # validate schema
        get_path = get_module_resource('record_of_employment', 'utils/xml_schema')
        # etree.XMLSchema(xmlschema_doc)
        schema = etree.XMLSchema(file=get_path + '/' + 'PayrollExtractXmlV2.xsd')
        # xml_doc = etree.parse(source=get_path + '/' + 'test.xml')
        xml_doc = etree.fromstring(xml_content.encode('utf-8'))
        # Validate the XML document

        try:
            if not schema.validate(xml_doc):
                schema.assert_(xml_doc)
            else:
                self.xml_content = xml_content

                # Prepare the file for download
                filename = f'{self.employee_id.name}' + '_ROE' + '.xml'
                content_type = 'application/xml'

                # Return the file as a response
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/?model=record.of.employee&field=xml_content&id=%s&filename=%s&content_type=%s' % (
                        self.id, filename, content_type),
                    'target': 'self',
                }
        except AssertionError as e:
            self.message_post(body=f"{e}")
        except Exception as e:
            self.message_post(body=f"{e}")

    def create_roe_xml(self):

        # Create the ROEHEADER element
        roeheader = ET.Element("ROEHEADER")
        roeheader.set("FileVersion", "W-2.0")
        roeheader.set("SoftwareVendor", "XYZ Software Vendor")
        roeheader.set("ProductName", "PS3000")

        # Create the ROE element
        roe = ET.SubElement(roeheader, "ROE")
        roe.set("PrintingLanguage", "E")
        roe.set("Issue", "D")

        # SERIAL AND PAYROLL INFORMATION
        if self.amended_serial_no:
            ET.SubElement(roe, "B2").text = str(self.amended_serial_no) or ""
        ET.SubElement(roe, "B3").text = str(self.employer_payroll_ref) or " "
        ET.SubElement(roe, "B5").text = str(self.cra_payroll_acc_num) or " "
        ET.SubElement(roe, "B6").text = str(self.pay_period_id.paystub_group_name.split(" ")[0][0]) or " "
        ET.SubElement(roe, "B8").text = str(self.social_insurance_number) or " "

        # EMPLOYEE INFORMATION
        b9 = ET.SubElement(roe, "B9")
        ET.SubElement(b9, "FN").text = self.employee_id.name.split(" ")[-1] or " "
        ET.SubElement(b9, "LN").text = self.employee_id.name.split(" ")[0] or " "
        ET.SubElement(b9, "A1").text = self.employee_id.private_street or " "
        ET.SubElement(b9, "A2").text = self.employee_id.private_city or " "
        ET.SubElement(b9, "A3").text = self.employee_id.private_country_id.name or " "
        ET.SubElement(b9, "PC").text = self.employee_id.private_zip or " "

        # PAY CYCLE INFORMATION
        ET.SubElement(roe, "B10").text = str(self.first_day_worked) or " "
        ET.SubElement(roe, "B11").text = str(self.last_day_worked) or " "
        ET.SubElement(roe, "B12").text = str(self.final_pay_period_ending_date) or " "
        ET.SubElement(roe, "B13").text = self.occupation or " "

        # EXPECTED DATE OF RECALL INFORMATION
        b14 = ET.SubElement(roe, "B14")
        ET.SubElement(b14, "CD").text = str(
            dict(self._fields['expected_date_of_recall'].selection).get(self.expected_date_of_recall).split("-")[
                0]) or " "

        ET.SubElement(roe, "B15A").text = str(round(self.total_insurable_hours)) or " "

        # INSURABLE EARNING INFORMATION
        b15c = ET.SubElement(roe, "B15C")
        for index, payslip in enumerate(self.get_payslip_ids(), start=1):
            pp = ET.SubElement(b15c, "PP")
            pp.set("nbr", str(index))
            ET.SubElement(pp, "AMT").text = str(round(payslip.insurable_earning, 2)) or " "

        # REASON FOR ISUEING THE ROE AND CONTACT INFORMATION
        b16 = ET.SubElement(roe, "B16")
        ET.SubElement(b16, "CD").text = str(
            dict(self._fields['reason_for_issuing_roe'].selection).get(self.reason_for_issuing_roe).split("-")[
                0]) if self.reason_for_issuing_roe else "" or " "
        ET.SubElement(b16, "FN").text = self.name_of_issuer_id.name.split(" ")[-1] if self.name_of_issuer_id else ""
        ET.SubElement(b16, "LN").text = self.name_of_issuer_id.name.split(" ")[0] if self.name_of_issuer_id else ""
        ET.SubElement(b16, "AC").text = "999"
        ET.SubElement(b16, "TEL").text = self.telephone_no

        # VACATION PAY INFORMATION
        b17a = ET.SubElement(roe, "B17A")
        vp = ET.SubElement(b17a, "VP")
        vp.set("nbr", "1")
        has_last_payment = self.vacation_pay_ids.filtered(lambda x: x.is_last_pay)

        ET.SubElement(vp, "CD").text = '2' if has_last_payment else '1'
        ET.SubElement(vp, "SDT").text = ''
        ET.SubElement(vp, "EDT").text = ''
        ET.SubElement(vp, "AMT").text = f'{has_last_payment[0].vacation_pay_amount:.2f}' if has_last_payment else ''

        # STATUTORY HOLIDAY INFORMATION
        b17b = ET.SubElement(roe, "B17B")
        sh = ET.SubElement(b17b, "SH")
        sh.set("nbr", "1")
        ET.SubElement(sh, "AMT").text = ''

        # OTHER MONIES INFORMATION
        b17c = ET.SubElement(roe, "B17C")
        om = ET.SubElement(b17c, "OM")
        om.set("nbr", "1")
        ET.SubElement(om, "CD").text = ''

        ET.SubElement(roe, "B18").text = self.comments
        ET.SubElement(roe, "B19").text = ''
        ET.SubElement(roe, "B20").text = 'E'

        # Create the XML tree
        tree = ET.ElementTree(roeheader)

        # Convert the XML tree to a string
        xml_str = ET.tostring(roeheader, encoding='utf-8', xml_declaration=True)

        # Return the XML string
        return xml_str.decode()

    def generate_roe_xml(self):
        # Call the function you created in step 2 to generate the T4 XML content
        xml_content = self.create_roe_xml()
        return xml_content

    # ===================== Download PDF ==========
    # ======================== Generate and download T4 PDF ===========================
    def download_roe_pdf(self):
        try:
            get_path = get_module_resource('record_of_employment', 'utils')
            output_folder_path = os.path.expanduser(os.getenv("HOME")) + "/outPdf/"
            if not os.path.isdir(output_folder_path):
                os.mkdir(output_folder_path)
            pdf_name = str(
                datetime.datetime.now().strftime(f"{self.employee_id.name.replace(' ', '')}-")) + str(
                datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".pdf"
            filename = output_folder_path + pdf_name

            reader = PdfReader(get_path + '/' + "roe.pdf")
            writer = PdfWriter()

            # page = reader.pages[0]
            # fields = reader.get_fields()

            writer.append(reader)

            # data = {'Slip1Year[0]': self.year,
            #         'Slip1EmployersName[0]': f'{self.employer_l1_nm}\n{self.employer_addr_l1_txt}\n{self.employer_cty_nm},{self.employer_prov_cd} {self.employer_pstl_cd}',
            #         'Slip1Box54[0]': None,
            #         'Slip1Box12[0]': self.employee_sin, 'Slip1Box14[0]': round(self.employee_empt_incamt, 2),
            #         'Slip1Box22[0]': round(self.income_itx_ddct_amt, 2), 'Slip1Box10[0]': 'ON',
            #         'Slip1Box16[0]': round(self.employee_cpp_cntrb_amt, 2),
            #         'Slip1Box24[0]': round(self.employee_ei_insu_ern_amt, 2), 'Slip1Box17[0]': 0.0,
            #         'Slip1Box26[0]': round(self.canada_cpp_qpp_ern_amt, 2),
            #         'Slip1Box18[0]': self.employee_empe_eip_amt,
            #         'Slip1Box44[0]': self.union_unn_dues_amt, 'Slip1Box20[0]': 0.0,
            #         'Slip1Box46[0]': self.charitable_chrty_dons_amt, 'Slip1Box52[0]': self.pension_padj_amt,
            #         'Slip1Box50[0]': self.employee_rpp_dpsp_rgst_nbr, 'Slip1Box55[0]': self.PPIP_prov_pip_amt,
            #         'Slip1Box56[0]': self.PPIP_prov_insu_ern_amt, 'Slip1LastName[0]': self.employee_snm,
            #         'Slip1FirstName[0]': self.employee_gvn_nm, 'Slip1Initial[0]': self.employee_init,
            #         'Slip1Address[0]': f'{self.employee_addr_l1_txt}\n{self.employee_addr_l2_txt}\n{self.employee_cty_nm}\n{self.employee_prov_cd} {self.employee_pstl_cd}',
            #         'Slip1Amount1[0]': None,
            #         'Slip1Amount2[0]': None, 'Slip1Amount3[0]': None, 'Slip1Amount4[0]': None,
            #         'Slip1Amount5[0]': None,
            #         'Slip1Amount6[0]': None, 'Slip1EmployersName[0].2': None,
            #         'Slip1Year[0].2': None, 'Slip1Box54[0].2': None, 'Slip1Box12[0].2': None,
            #         'Slip1Box14[0].2': None,
            #         'Slip1Box22[0].2': None, 'Slip1Box16[0].2': None, 'Slip1Box24[0].2': None,
            #         'Slip1Box17[0].2': None,
            #         'Slip1Box26[0].2': None, 'Slip1Box18[0].2': None, 'Slip1Box44[0].2': None,
            #         'Slip1Box20[0].2': None,
            #         'Slip1Box46[0].2': None, 'Slip1Box52[0].2': None, 'Slip1Box50[0].2': None,
            #         'Slip1Box55[0].2': None,
            #         'Slip1Box56[0].2': None, 'Slip1LastName[0].2': None, 'Slip1FirstName[0].2': None,
            #         'Slip1Initial[0].2': None, 'Slip1Address[0].2': None, 'Slip1Amount1[0].2': None,
            #         'Slip1Amount2[0].2': None, 'Slip1Amount3[0].2': None, 'Slip1Amount4[0].2': None,
            #         'Slip1Amount5[0].2': None, 'Slip1Amount6[0].2': None}
            has_last_payment = self.vacation_pay_ids.filtered(lambda x: x.is_last_pay)
            self.vacation_pay_amount = f'{has_last_payment[0].vacation_pay_amount:.2f}' if has_last_payment else ''
            data = {
                'sl_no': self.serial_no or '',
                'employee_info': f'{self.employee_id.name}\n{self.employee_id.private_street},{self.employee_id.private_street2},{self.employee_id.private_city},{self.employee_id.private_country_id.name}' or '',
                'employer_info': f'{self.name_of_issuer_id.name}\n{self.name_of_issuer_id.private_street},{self.name_of_issuer_id.private_street2},{self.name_of_issuer_id.private_city},{self.name_of_issuer_id.private_country_id.name}' or '',
                'pay_period_type': self.pay_period_id.paystub_group_name or '',
                'unique_id2': '',
                'employer_payroll_ref': self.employer_payroll_ref or '',
                'sl_issue_no': self.social_insurance_number or '',
                'first_day': self.first_day_worked or '',
                'last_day_paid': self.last_day_worked or '',
                'final_pay_period': self.final_pay_period_ending_date or '',
                'occupation': self.occupation or '',
                'total_insurance_hour': round(self._get_insurable_hour(), 2) or '',
                'total_insurance_earning': self._get_insurable_earning() or '',
                'exp_date_recall': dict(self._fields['expected_date_of_recall'].selection).get(
                    self.expected_date_of_recall) or '',
                'reason': dict(self._fields['reason_for_issuing_roe'].selection).get(self.reason_for_issuing_roe) or '',
                'telephone1': self.telephone_no or '',
                'telephone2': self.telephone_no or '',
                'sl_roe': self.amended_serial_no or '',
                'postal_code': self.employee_id.private_zip or '',
                'cra_payroll_acc': self.cra_payroll_acc_num or '',
                'issuer_name': self.name_of_issuer_id.name or '',
                'issue_date': datetime.datetime.now().date() or '',
                'vacation_pay': self.vacation_pay_amount or '',
                'vacation_pay_start': self.vacation_pay_start_date or '',
                'vacation_pay_end': self.vacation_pay_end_date or '',
                'comment': self.comments or '',
                'other_start_date1': '',
                'other_start_date2': '', 'other_start_date3': '', 'other_end_date1': '',
                'other_end_date2': '', 'other_end_date3': '',
                'CheckBox-14Yj7BWRzb': '', 'CheckBox-QFXjTBRVwq': '', 'CheckBox-f1WzgWGwMl': '',
                'CheckBox-djIjiRzJE7': '', 'CheckBox-3o38tjRP62': '', 'CheckBox-4qOCRr9Nrz': '',
                'CheckBox-eTaQV6ngRM': '', 'CheckBox-7aZtgMItxj': '',
                'comm_english': '', 'comm_french': '',
                'unique_id': '', 'Text-9vMCmQF1F1': '',
                'Text-yk2dZTKG-c': '', 'Text-0K3CUNZijm': '', 'Text-_e_t278CcP': '',
                'Text-UA8BMNPK9-': '', 'Text-nvSTgcUKe2': '', 'Text-qSSHJVKGp9': '',
                'Text-InbjcxfE6o': '', 'amount1': '', 'amount2': '', 'amount3': '', 'amount4': '',
                'holiday_pay': '',

            }
            for index, payslip in enumerate(self.get_payslip_ids(), start=1):
                date_field = f'pay_period_ending_date{index}'
                hours_field = f'insurable_hours{index}'
                earning_field = f'insurable_earning{index}'

                data[date_field] = payslip.date_to
                data[hours_field] = round(payslip.insurable_hour, 2)
                data[earning_field] = payslip.insurable_earning

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

        return {
            'type': 'ir.actions.act_url',
            'url': '/download/pdf?file_path=%s&file_name=%s' % (filename, pdf_name),
            'target': 'new',
        }
