import requests
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils

PAYGROUP = {
    'monthly': 'Monthly',
    'quarterly': 'Quarterly',
    'semi-annually': 'Semi-annually',
    'annually': 'Annually',
    'weekly': 'Weekly',
    'bi-weekly': 'Bi-weekly',
    'bi-monthly': 'Bi-monthly',
}


class InheritedHrPayslip(models.Model):
    _inherit = 'hr.payslip'

    paid_date = fields.Date(string="Paid Date", readonly=True, store=True, copy=False,
                            )

    pay_cycle = fields.Many2one('paycycle.config', related='contract_id.salary_pay_cycle', readonly=True)
    pay_cycle_period = fields.Many2one('paycycle.period')
    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)
    is_manual_input = fields.Boolean(compute='_compute_is_manual_input')

    irre_amount = fields.Float("Irregular Amount",default=0)

    #====================need to remove=====================
    irre_fed_tax = fields.Float("Irregular Fed Tax",default=0)
    irre_prov_tax = fields.Float("Irregular Prov Tax",default=0)




    def _compute_is_manual_input(self):
        with_user = self.env['ir.config_parameter'].sudo()
        attendance_manual = with_user.get_param('syncoria_can_payroll.attendance_manual_input')
        for payslip in self:
            payslip.is_manual_input = True if attendance_manual == 'True' else False

    # ============ Base overided method ===================
    @api.depends('employee_id', 'struct_id', 'date_from')
    def _compute_name(self):
        super(InheritedHrPayslip, self)._compute_name()
        for slip in self.filtered(lambda p: p.employee_id and p.date_from):
            if slip.payslip_run_id:
                slip.update({
                    'pay_cycle_period': slip.payslip_run_id.pay_cycle_period,
                })

    # ======================================================

    @api.depends('pay_cycle')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle:
                rec.pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_ids.filtered(
                    lambda x: x.paycycle_config_id.id == rec.pay_cycle.id).ids

    @api.onchange('pay_cycle_period')
    def _onchange_pay_cycle_period(self):
        for rec in self:
            if rec.pay_cycle_period:
                rec.update({
                    'name': rec.pay_cycle_period.name + f'-{fields.Date.today().year}',
                    'date_from': rec.pay_cycle_period.start_date,
                    'date_to': rec.pay_cycle_period.end_date
                })

    @api.onchange('payslip_run_id')
    def _onchange_pay_payslip_run_id(self):
        for rec in self:
            if rec.payslip_run_id:
                if rec.payslip_run_id.pay_cycle != rec.pay_cycle:
                    raise UserError(_("Batch pay cycle is not matched with contract pay cycle!"))
                rec.update({
                    'pay_cycle_period': rec.payslip_run_id.pay_cycle_period,
                })

    def action_payslip_paid(self):
        if any(slip.state not in ['done', 'waiting'] for slip in self):
            raise UserError(_('Cannot mark payslip as paid if not confirmed or waiting.'))
        self.write({'state': 'paid', 'paid_date': fields.Date.today()})
        # ================= YTD Information Update =========
        # for slip in self:
        #     slip.employee_id.with_context({"type":"ALL"}).update_ytd_erp() # "ALL" is for update YTD of CPP,CPP2,PI
        #     slip.employee_id.update_ytd_irregular_payments_tax() # "ALL" is for update YTD of CPP,CPP2,PI

    def action_payslip_cancel(self):
        super(InheritedHrPayslip,self).action_payslip_cancel()
        for slip in self:
            slip.employee_id.with_context({"type":"ALL"}).update_ytd_erp() # "ALL" is for update YTD of CPP,CPP2,PI
            slip.employee_id.update_ytd_irregular_payments_tax() # "ALL" is for update YTD of CPP,CPP2,PI

    def get_previous_irregular_payment(self, id, paycycle):
        payslip = self.browse(id)
        payslip_employee = payslip.employee_id
        payslip_date_year = payslip.date_from.year
        payslip_with_irregular_payment_line_ids = payslip_employee.slip_ids.filtered(
            lambda x: x.state == 'paid' and x.input_line_ids and (
                x.paid_date.year if x.paid_date else x.write_date.year) == payslip_date_year).line_ids
        payslip_with_irregular_payment_amount = 0.0
        if payslip_with_irregular_payment_line_ids:
            payslip_with_irregular_payment_amount = sum(
                payslip_with_irregular_payment_line_ids.filtered(lambda x: x.category_id.code in ["ADD_ALLOWANCE"]).mapped("total"))

        return payslip_with_irregular_payment_amount + payslip_employee.ytd_previous_irre_prov_amount


    def write(self, vals):
        res = super(InheritedHrPayslip,self).write(vals)
        for rec in self:
            if rec.payslip_run_id and res and 'state' in vals and vals.get('state') == 'paid':
                rec.payslip_run_id._check_paid_status()
            if 'state' in vals and vals.get('state') == 'paid':
                rec.employee_id.with_context({"type": "ALL"}).update_ytd_erp()
                rec.write({
                    'irre_amount': sum([line.amount for line in rec.line_ids if line.salary_rule_id.is_irregular_payment])

                })
                rec.employee_id.update_ytd_irregular_payments_tax()
        return res

    # ================== Report ======================
    def _get_paygroup(self, value):
        return PAYGROUP.get(value)

    def action_print_rgr_report(self):
        return self.env.ref('syncoria_can_payroll.action_report_rgr').report_action(self)

    # ================= Salry Rules ==========================

    def get_gross_amount(self,pay_slip):
        rec = self.browse(pay_slip)
        result = 0.0
        try:
            is_pay_cycle = rec.contract_id.salary_pay_cycle.pay_cycle
            gross_work_entry_type = self.env['hr.work.entry.type'].search([('is_gross', '=',True)])
            deduct_from_gross_work_entry_type = self.env['hr.work.entry.type'].search([('deduct_from_gross', '=',True)])
            result += sum([round(rec._get_worked_days_line_amount(gross_entry_type.code),2) if gross_entry_type.code else 0.0 for gross_entry_type in gross_work_entry_type])
            result -= sum([round(rec._get_worked_days_line_amount(deduct_gross_entry_type.code),2) if deduct_gross_entry_type.code else 0.0 for deduct_gross_entry_type in deduct_from_gross_work_entry_type])
            if is_pay_cycle and not rec.contract_id.is_hourly:
                if rec.contract_id.work_entry_source in ['attendance','calendar']:
                    result += round(rec._get_worked_days_line_amount('WORK100'),2)
            elif is_pay_cycle and rec.contract_id.is_hourly:
                if rec.contract_id.work_entry_source in ['attendance','calendar']:
                    result += round(rec._get_worked_days_line_amount('WORK100'),2)
                elif rec.contract_id.work_entry_source == 'timesheet_hours':
                    result += round(rec._get_worked_days_line_amount('TIMESHEET_WORK100'),2)
                else:
                    result = 0.0
            else:
                result = 0.0
        except:
            pass

        return result


    # ================== Work days line based on manual input ==============
    def compute_workdays_manual_input(self,manual_input_ids):
        """
        Here this function will only trigger when batch payslip will only generate
        by "Manually Generate Payslips" button.
        """
        for rec in self:
            manual_input_line_id = manual_input_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            attendance_hour = manual_input_line_id.attendance_hours
            avg_working_hour_per_day = rec.contract_id.resource_calendar_id.hours_per_day
            rec.worked_days_line_ids.unlink()
            worked_days_lines = []
            if attendance_hour > 0.0:
                worked_days_lines.append((0, 0, {
                    'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                    'name': 'Attendance',
                    'number_of_days': attendance_hour / avg_working_hour_per_day,
                    'number_of_hours': attendance_hour,
                    # 'amount': timesheet_hours*payslip.contract_id.hourly_rate

                }))

            rec.worked_days_line_ids = worked_days_lines

    #================ For Unique Work entry type ========
    # @api.constrains('worked_days_line_ids')
    # def _check_unique_worked_entry_type(self):
    #     unique_work_entry_type_ids = []
    #     for line in self.worked_days_line_ids:
    #         if line.work_entry_type_id.id in unique_work_entry_type_ids:
    #             raise ValidationError('Worked Entry Type must be unique per payslip.')
    #         unique_work_entry_type_ids.append(line.work_entry_type_id.id)

        # ================== For Version 17 no need schedule pay =================

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_warning_message(self):
        for slip in self.filtered(lambda p: p.date_to):
            slip.warning_message = False
            warnings = []
            if slip.contract_id and (slip.date_from < slip.contract_id.date_start
                                     or (slip.contract_id.date_end and slip.date_to > slip.contract_id.date_end)):
                warnings.append(_("The period selected does not match the contract validity period."))

            if slip.date_to > date_utils.end_of(fields.Date.today(), 'month'):
                warnings.append(_(
                    "Work entries may not be generated for the period from %(start)s to %(end)s.",
                    start=date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1),
                    end=slip.date_to,
                ))

            # if (slip.contract_id.schedule_pay or slip.contract_id.structure_type_id.default_schedule_pay) \
            #         and slip.date_from + slip._get_schedule_timedelta() != slip.date_to:
            #     warnings.append(_("The duration of the payslip is not accurate according to the structure type."))

            if warnings:
                warnings = [_("This payslip can be erroneous :")] + warnings
                slip.warning_message = "\n  ・ ".join(warnings)

    def _action_create_account_move(self):
        res = super(InheritedHrPayslip, self)._action_create_account_move()

        for slip in self:
            if slip.date_to:
                slip.date = slip.date_to
                slip.move_id.date = slip.date_to

        return res

    # email send to customer --------------------
    # def _get_payslip_pdf_reports(self):
    #     classic_report = self.env.ref('hr_payroll.action_report_payslip')
    #     result = defaultdict(lambda: self.env['hr.payslip'])
    #     for payslip in self:
    #         if not payslip.struct_id or not payslip.struct_id.report_id:
    #             result[classic_report] |= payslip
    #         else:
    #             result[payslip.struct_id.report_id] |= payslip
    #     return result
    #
    # @api.model
    # def _get_email_template(self):
    #     return self.env.ref(
    #         'hr_payroll.mail_template_new_payslip', raise_if_not_found=False
    #     )

    # def action_payslip_email_send(self):
    #     mapped_reports = self._get_payslip_pdf_reports()
    #     attachments_vals_list = []
    #     generic_name = _("Payslip")
    #     template = self._get_email_template()
    #     print('template', template)
    #     print('mapped_reports', mapped_reports)
    #     for report, payslips in mapped_reports.items():
    #         for payslip in payslips:
    #             pdf_content, dummy = self.env['ir.actions.report'].sudo().with_context(lang=payslip.employee_id.lang)._render_qweb_pdf(report, payslip.id)
    #             if report.print_report_name:
    #                 pdf_name = safe_eval(report.print_report_name, {'object': payslip})
    #             else:
    #                 pdf_name = generic_name
    #             attachments_vals_list.append({
    #                 'name': pdf_name,
    #                 'type': 'binary',
    #                 'raw': pdf_content,
    #                 'res_model': payslip._name,
    #                 'res_id': payslip.id
    #             })
    #             # Send email to employees
    #             if template:
    #                 template.send_mail(payslip.id, email_layout_xmlid='mail.mail_notification_light')
    #     self.env['ir.attachment'].sudo().create(attachments_vals_list)

    def action_payslip_email_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('syncoria_can_payroll.email_template_for_payslip')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
            print('compose_form_id', compose_form_id)
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
        })

        ctx['model_description'] = _('Payslip')
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def compute_sheet(self):
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'])
        payslips.line_ids.unlink()
        self.env.flush_all()
        today = fields.Date.today()
        for payslip in payslips:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            payslip.write({
                'number': number,
                'state': 'verify',
                'compute_date': today
            })

            # Customised code start *****************************************************
            # API endpoint
            url = "http://127.0.0.1:8000/api/v1/payroll_info/calculate-tax/"
            pay_lines = payslips._get_payslip_lines()
            I = 0
            F = 0
            B = 0
            for x in pay_lines:
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).is_irregular_payment:
                    B += x['amount']
                if x['code'] == 'GROSS':
                    I = x['amount']
                if x['code'] == 'RRSP':
                    F = x['amount']

            # Parameters for the API request
            P = payslip.pay_cycle.pay_cycle
            D = payslip.employee_id.ytd_cpp
            D1 = payslip.employee_id.ytd_ei
            D2 = payslip.employee_id.ytd_cpp2
            ytd_pi = payslip.employee_id.ytd_pi
            emp_province = payslip.employee_id.territory_of_employment.code
            # B1 = payslip.employee_id.year_to_date_irregular_payment
            B1 = 0 #TODO place the real data
            federal_amount_from_td1 = payslip.contract_id.federal_amount_from_td1
            proviancial_amount_from_td1 = payslip.contract_id.proviancial_amount_from_td1
            date_of_birth = str(payslip.employee_id.birthday)
            if date_of_birth == 'False':
                raise ValidationError("Employee Date of Birth Mandatory")
            payroll_year = payslip.date_to.year
            payload = {
                    "I": I,
                    "P": P,
                    "B": B,
                    "B1": B1,
                    "D": D,
                    "F": F,
                    "F1": 0,
                    "F2": 0,
                    "F3": 0,
                    "F4": 0,
                    "D1": D1,
                    "D2": D2,
                    "YTD_PI": ytd_pi,
                    "TC": federal_amount_from_td1,
                    "TCP": proviancial_amount_from_td1,
                    "LCF": 0,
                    "U1": 0,
                    "HD": 0,
                    "LCP": 0,
                    "num_of_disabled_dep": 0,
                    "num_of_dep_19": 0,
                    "payroll_year": payroll_year,
                    "emp_province": emp_province,
                    "date_of_birth": date_of_birth
                }
            # Make the API call
            try:
                response = requests.post(url, json=payload)
                response_data = response.json()

            except Exception as e:
                raise ValidationError(f"Failed to call the API: {str(e)}")

            # Add FTAX and OTAX in Lines ************
            positive_amount_cat_list = ["GROSS", "ADD_ALLOWANCE", "ALW"]
            neg_amount_cat_list = ["DED", "PRE_TAX_DEDUCTION", "POST_TAX_DEDUCTION"]
            positive_amount = 0
            neg_amount = 0
            for x in pay_lines:
                category_code = self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).category_id.code
                if x['code'] == 'FTAX':
                    x['amount'] = response_data['FTAX'] if response_data else 0
                if x['code'] == 'OTAX':
                    x['amount'] = response_data['OTAX'] if response_data else 0

                # add category wise amounts for net calculation******************
                if category_code in positive_amount_cat_list:
                    positive_amount += x['amount']
                elif category_code in neg_amount_cat_list:
                    neg_amount += x['amount']

                # place the net amount
                if x['code'] == 'NET':
                    x['amount'] = positive_amount - neg_amount

            self.env['hr.payslip.line'].create(pay_lines)
        return True
