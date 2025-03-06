
from PyPDF2 import PdfFileMerger
from odoo import fields, models, api, _
import os
import xml.etree.ElementTree as ET
from lxml import etree
from odoo.exceptions import UserError

from odoo.modules.module import get_module_resource
from datetime import datetime

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
    expected_date = fields.Date(string="Date Of Recall" ,default=fields.Date.today())
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
    name_of_issuer_id = fields.Many2one(
        "hr.employee",
        string="22-Name of Issuer",

    )
    payslip_ids = fields.One2many("hr.payslip", "roe_id", string="15c-PaySlip")
    vacation_pay_ids = fields.One2many("hr.vacation.pay", "roe_id", string="Vacation Pay")
    vacation_amount_ids = fields.One2many("vacation.amount", "roe_id", string="Vacation Pay")

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

    def _get_vacation_amount(self):
        self.write({'vacation_amount_ids': [(5, 0, 0)]})

        payslips = self.get_payslip_ids()
        adjusted_input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_adjusted_vac_pay').id
        input_type = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id
        vacation_data = []

        for payslip in payslips:
            # Retrieve vacation input lines
            vac_info = payslip.input_line_ids.search([
                ("payslip_id", "=", payslip.id),
                ("input_type_id", "in", [adjusted_input_type, input_type])
            ])

            # Sum up the vacation amounts if needed
            total_vacation_amount = sum(line.amount for line in vac_info)
            if vac_info:

                vacation_data.append((0, 0, {
                    "payslip_id": payslip.id,
                    "reference":payslip.number,
                    "vacation_pay_type": [(6, 0, vac_info.ids)],  # Use Many2many relation with the input records
                    "amount": total_vacation_amount,
                }))

        # Insert data into the One2many field
        return vacation_data

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
            has_last_payment = self.vacation_amount_ids.sorted(key=lambda r: r.reference, reverse=True)[:1]

            line_obj = self.employee_id.payroll_line_ids.filtered(lambda x: x.year == datetime.now().year)
            self.write({
                "company_id": employee.company_id,
                "name_of_issuer_id" : self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id,
                "pay_period_id": employee.contract_id.salary_pay_cycle,
                "social_insurance_number": employee.identification_id,
                "first_day_worked": employee.contract_id.date_start,
                "last_day_worked": employee.contract_id.date_end,
                "final_pay_period_ending_date": payslip_ids[0].date_to if payslip_ids else '',
                "occupation": employee.job_id.name,
                "cra_payroll_acc_num": employee.company_id.payroll_account_number,
                "employer_payroll_ref": self.company_id.employer_payroll_ref or '',
                "total_insurable_hours": self._get_insurable_hour(),
                "total_insurable_earnings": line_obj.ytd_pi,
                "payslip_ids": payslip_ids,
                "vacation_amount_ids": self._get_vacation_amount(),
                "vacation_pay_amount": round(has_last_payment.amount,2) if has_last_payment else ''
            })

        # ======================== Generate and download T4 xml ===========================

    def download_roe_xml(self):
        # Generate the T4 XML content
        for rec in self:
            xml_content = rec.generate_roe_xml()

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
                    rec.xml_content = xml_content

                    # Prepare the file for download
                    filename = f'{rec.employee_id.name}' + '_ROE' + '.xml'
                    content_type = 'application/xml'

                    # Return the file as a response
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/download/roe/?model=record.of.employee&field=xml_content&id=%s&filename=%s&content_type=%s' % (
                            rec.id, filename, content_type),
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
        ET.SubElement(b14, "DT").text = "" if self.expected_date_of_recall != 'expected_date_recall' else str(self.expected_date)


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
        has_last_payment =  self.vacation_amount_ids.sorted(key=lambda r: r.reference, reverse=True)[:1]

        ET.SubElement(vp, "CD").text = '2' if has_last_payment else '1'
        ET.SubElement(vp, "SDT").text = ''
        ET.SubElement(vp, "EDT").text = ''
        ET.SubElement(vp, "AMT").text = f'{has_last_payment.amount:.2f}' if has_last_payment else ''

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


    def download_roe_pdf(self, is_bulk=False):

        kwrgs =[]
        for rec in self:
            if rec.state == 'done':
                try:
                    get_path = get_module_resource('record_of_employment', 'utils')
                    output_folder_path = os.path.expanduser(os.getenv("HOME")) + "/outPdf/"
                    if not os.path.isdir(output_folder_path):
                        os.mkdir(output_folder_path)

                    pdf_name = str(
                        datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-")) + str(
                        datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".pdf"

                    filename = output_folder_path + pdf_name

                    reader = PdfReader(get_path + '/' + "roe.pdf")
                    writer = PdfWriter()

                # page = reader.pages[0]
                # fields = reader.get_fields()

                    writer.append(reader)
                    rec.compute_roe()

                    has_last_payment =  self.vacation_amount_ids.sorted(key=lambda r: r.reference, reverse=True)[:1]
                    rec.vacation_pay_amount = f'{has_last_payment.amount:.2f}' if has_last_payment else ''
                    data = {
                        'sl_no': rec.serial_no or '',
                        'employee_info': f'{rec.employee_id.name}\n{rec.employee_id.private_street or ""},{rec.employee_id.private_street2 or ""},{rec.employee_id.private_city or ""},{rec.employee_id.private_country_id.name or ""}' or '',
                        'employer_info': f'{rec.name_of_issuer_id.name}\n{rec.name_of_issuer_id.private_street or ""},{rec.name_of_issuer_id.private_street2 or ""},{rec.name_of_issuer_id.private_city or ""},{rec.name_of_issuer_id.private_country_id.name or ""}' or '',
                        'pay_period_type': rec.pay_period_id.paystub_group_name or '',
                        'unique_id2': '',
                        'employer_payroll_ref': rec.employer_payroll_ref or '',
                        'sl_issue_no': rec.social_insurance_number or '',
                        'first_day': rec.first_day_worked.strftime('%d-%m-%Y') or '',
                        'last_day_paid': rec.last_day_worked.strftime('%d-%m-%Y') if rec.last_day_worked else '' or '',
                        'final_pay_period': rec.final_pay_period_ending_date.strftime('%d-%m-%Y') or '',
                        'occupation': rec.occupation or '',
                        'total_insurance_hour': round(rec._get_insurable_hour(), 2) or '',
                        'total_insurance_earning': rec._get_insurable_earning() or '',
                        'exp_date_recall': dict(rec._fields['expected_date_of_recall'].selection).get(
                            rec.expected_date_of_recall) or '' if rec.expected_date_of_recall != 'expected_date_recall' else rec.expected_date.strftime('%d-%m-%Y'),
                        'reason': dict(rec._fields['reason_for_issuing_roe'].selection).get(rec.reason_for_issuing_roe) or '',
                        'telephone1': rec.telephone_no or '',
                    'telephone2': rec.telephone_no or '',
                    'sl_roe': rec.amended_serial_no or '',
                    'postal_code': rec.employee_id.private_zip or '',
                    'cra_payroll_acc': rec.cra_payroll_acc_num or '',
                    'issuer_name': rec.name_of_issuer_id.name or '',
                    'issue_date': datetime.now().strftime('%d-%m-%Y') or '',
                    'vacation_pay': rec.vacation_pay_amount or '',
                    'vacation_pay_start': rec.vacation_pay_start_date.strftime('%d-%m-%Y') if rec.vacation_pay_start_date else '',
                    'vacation_pay_end': rec.vacation_pay_end_date.strftime('%d-%m-%Y') if rec.vacation_pay_end_date else '',
                    'comment': rec.comments or '',
                    'other_start_date1': None,
                    'other_start_date2': None, 'other_start_date3': None, 'other_end_date1': None,
                    'other_end_date2': None, 'other_end_date3': None,
                    'CheckBox-14Yj7BWRzb': None, 'CheckBox-QFXjTBRVwq': None, 'CheckBox-f1WzgWGwMl': None,
                    'CheckBox-djIjiRzJE7': None, 'CheckBox-3o38tjRP62': None, 'CheckBox-4qOCRr9Nrz': None,
                    'CheckBox-eTaQV6ngRM': None, 'CheckBox-7aZtgMItxj': None,
                    'comm_english': None, 'comm_french': None,
                    'unique_id': None, 'Text-9vMCmQF1F1': None,
                    'Text-yk2dZTKG-c': None, 'Text-0K3CUNZijm': None, 'Text-_e_t278CcP': None,
                    'Text-UA8BMNPK9-': None, 'Text-nvSTgcUKe2': None, 'Text-qSSHJVKGp9': None,
                    'Text-InbjcxfE6o': None, 'amount1': None, 'amount2': None, 'amount3': None, 'amount4': None,
                    'holiday_pay': None,

                    }
                    for index, payslip in enumerate(rec.get_payslip_ids(), start=1):
                        date_field = f'pay_period_ending_date{index}'
                        hours_field = f'insurable_hours{index}'
                        earning_field = f'insurable_earning{index}'

                        data[date_field] = payslip.date_to.strftime('%d-%m-%Y')
                        data[hours_field] = round(payslip.insurable_hour, 2)
                        data[earning_field] = payslip.insurable_earning

                    # Fetch values from employee_id.roe_paycycle_ids and continue numbering
                    paycycle_index = index + 1  # Continue numbering from last payslip index

                    for paycycle in rec.employee_id.roe_paycycle_ids:
                        date_field = f'pay_period_ending_date{paycycle_index}'
                        hours_field = f'insurable_hours{paycycle_index}'
                        earning_field = f'insurable_earning{paycycle_index}'

                        data[date_field] = paycycle.pay_period_date.strftime(
                            '%d-%m-%Y') if paycycle.pay_period_date else ''
                        data[hours_field] = round(paycycle.insurable_hour, 2)
                        data[earning_field] = paycycle.insurable_earning

                        paycycle_index += 1  # Increment index
                    data = {key: str(value) if value is not None else "" for key, value in data.items()}
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


                kwrgs.append((filename,pdf_name))
                if is_bulk:  # Change the PDF name if called from the action
                    pdf_name = "Merged_ROE.pdf"

        return {
            'type': 'ir.actions.act_url',
            'url': '/download/pdf?file_path=%s&file_name=%s&file_paths=%s' % ('', pdf_name,kwrgs),
            'target': 'new',
        }

    def send_roe_xml_batch(self):
        files_list=[]
        mail_template = self.env.ref('record_of_employment.email_template_batch_roe_xml')
        mail_template.attachment_ids =[]
        for rec in self:
            xml_content = rec.generate_roe_xml()
            rec.xml_content = xml_content

            attachment = self.env['ir.attachment'].create({
                'name':  str(
                        datetime.now().strftime(f"{rec.employee_id.name.replace(' ', '')}-")) + str(
                        datetime.now().strftime("%m%d%Y%H%M%S%f")) + ".xml",
                'raw': xml_content,
                'res_id': rec.id,
                'res_model': 'record.of.employee',
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            files_list.append((4, attachment.id))


        # mail_template.attachment_ids = files_list
        email_values = {
            "attachment_ids":files_list
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


class VacationAmount(models.Model):
    _name = "vacation.amount"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vacation Amount"

    roe_id = fields.Many2one("record.of.employee")
    payslip_id = fields.Many2one("hr.payslip")
    reference= fields.Char()
    vacation_pay_type = fields.Many2many("hr.payslip.input")
    amount = fields.Float(string="Amount")
