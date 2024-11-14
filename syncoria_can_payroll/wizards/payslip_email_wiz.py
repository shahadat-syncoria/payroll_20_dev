from odoo import models, fields, api
import base64
from collections import defaultdict


class PayslipEmailWizard(models.TransientModel):
    _name = 'payslip.email.wizard'
    _description = 'Payslip Email Wizard'

    employee_ids = fields.Many2many('hr.employee',string="Employee(s)")
    payslip_ids = fields.Many2many('hr.payslip',string="Payslip(s)")

    def default_get(self, fields):
        defaults = super(PayslipEmailWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            payslip_records = self.env['hr.payslip'].browse(active_ids)
            employee_ids = list(set(payslip_records.mapped('employee_id.id')))
            defaults['employee_ids'] = [(6, 0, employee_ids)]
            defaults['payslip_ids'] = [(6, 0, active_ids)]

        return defaults

    # Fetch the PDF reports for the payslip
    def _get_payslip_pdf_reports(self,payslip_obj):
        classic_report = self.env.ref('hr_payroll.action_report_payslip')
        result = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslip_obj:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                result[classic_report] |= payslip
            else:
                result[payslip.struct_id.report_id] |= payslip
        return result

    # Fetch the email template
    @api.model
    def _get_email_template(self):
        return self.env.ref(
            # 'hr_payroll.mail_template_new_payslip', raise_if_not_found=False
            'syncoria_can_payroll.bulk_email_template_for_payslip', raise_if_not_found=False
        )

    def action_payslip_email_send(self):
        template = self._get_email_template()
        if not template:
            return
        # Generate the PDF reports
        for x in self.payslip_ids:
            mapped_reports = self._get_payslip_pdf_reports(x)
            attachments_vals_list = []
            for report, payslips in mapped_reports.items():
                for payslip in x:
                    pdf_content, dummy = self.env['ir.actions.report'].sudo().with_context(
                        lang=payslip.employee_id.lang
                    )._render_qweb_pdf(report, payslip.id)
                    pdf_content_encoded = base64.b64encode(pdf_content).decode('utf-8')
                    pdf_name = 'Payslip'
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': pdf_name,
                        'type': 'binary',
                        'datas': pdf_content_encoded,
                        'res_model': 'hr.payslip',
                        'res_id': payslip.id,
                        'mimetype': 'application/pdf'
                    })
                    attachments_vals_list.append(attachment.id)

            # Prepare and send the email
            subject = template.subject.replace('$employee', x.employee_id.name).replace('$ref', x.name)
            body_html = template.body_html.replace('$employee', x.employee_id.name)
            mail_values = {
                'email_from': x.env.user.company_id.email,
                'email_to': x.employee_id.work_email,
                'subject': subject,
                'body_html': body_html,
                'attachment_ids': [(6, 0, attachments_vals_list)],
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()


