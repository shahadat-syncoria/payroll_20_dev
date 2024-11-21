import requests
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from odoo import api, models, _


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
    api_response_json = fields.Json()
    api_payload_json = fields.Json()

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
                rec.write({
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
    def compute_workdays_manual_input(self, manual_input_ids):
        """
        Here this function will only trigger when batch payslip will only generate
        by "Manually Generate Payslips" button.
        """
        for rec in self:
            manual_input_line_id = manual_input_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            attendance_hour = manual_input_line_id.attendance_hours
            over_time_hour = manual_input_line_id.overtime_hours
            stat_over_time_hour = manual_input_line_id.stat_overtime_hours

            vac_pay = manual_input_line_id.vac_pay
            bonus = manual_input_line_id.bonus
            commission = manual_input_line_id.commission
            retro = manual_input_line_id.retro

            rec.payout_vacation_pay_paycycle = True if manual_input_line_id.payout_vacation_pay_paycycle else False

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
            # if over_time_hour > 0.0:
            #     worked_days_lines.append((0, 0, {
            #         'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
            #         'name': 'Overtime',
            #         'number_of_days': over_time_hour / avg_working_hour_per_day,
            #         'number_of_hours': over_time_hour,
            #         # 'amount': timesheet_hours*payslip.contract_id.hourly_rate
            #
            #     }))
            # if stat_over_time_hour > 0.0:
            #     worked_days_lines.append((0, 0, {
            #         'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_stat_overtime_work_entry_type').id,
            #         'name': 'Statutory Holidays Overtime',
            #         'number_of_days': stat_over_time_hour / avg_working_hour_per_day,
            #         'number_of_hours': stat_over_time_hour,
            #         # 'amount': timesheet_hours*payslip.contract_id.hourly_rate
            #
            #     }))

            rec.worked_days_line_ids = worked_days_lines
            input_line = []
            if vac_pay > 0.0:
                input_line.append((0, 0, {
                    'input_type_id': self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay').id,
                    'name': "Vacation Pay",
                    'amount': vac_pay,
                }))
            if bonus > 0.0:
                input_line.append((0, 0, {
                    'input_type_id': self.env.ref('syncoria_can_irregular_payment.input_ca_bonus_pay').id,
                    'name': "Bonus",
                    'amount': bonus,
                }))

            if commission > 0.0:
                input_line.append((0, 0, {
                    'input_type_id': self.env.ref('syncoria_can_irregular_payment.input_ca_commission').id,
                    'name': "Commission",
                    'amount': commission,
                }))
            if retro > 0.0:
                input_line.append((0, 0, {
                    'input_type_id': self.env.ref('syncoria_can_irregular_payment.input_ca_retro_pay').id,
                    'name': "Retro",
                    'amount': retro,
                }))

            rec.input_line_ids = input_line

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

    def action_payslip_email_send(self):
        self.ensure_one()
        if not self.state in ('verify', 'done', 'paid'):
            raise UserError("Email can not be sent in this state!")
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup('syncoria_can_payroll.email_template_for_payslip')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
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

    # inherited compute_sheet method for tax api call
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
            pay_lines = payslip._get_payslip_lines()
            I = 0
            F = 0
            B = 0
            V = 0
            V_list = ['ADJUST_VP','VP']
            for x in pay_lines:
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).is_irregular_payment:
                    B += x['amount']
                if x['code'] == 'GROSS':
                    I = x['amount']
                if x['code'] in V_list:
                    V += x['amount']
                if x['code'] == 'RRSP':
                    F = x['amount']
            # Parameters for the API request
            P = payslip.pay_cycle.pay_cycle
            D = payslip.employee_id.ytd_cpp
            D1 = payslip.employee_id.ytd_ei
            D2 = payslip.employee_id.ytd_cpp2
            ytd_pi = payslip.employee_id.ytd_pi
            emp_province = payslip.employee_id.territory_of_employment.code
            B1 = payslip.employee_id.year_to_date_irregular_payment
            # B1 = 0 #TODO place the real data
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
                    "V": V,
                    "HD": 0,
                    "LCP": 0,
                    "num_of_disabled_dep": 0,
                    "num_of_dep_19": 0,
                    "payroll_year": payroll_year,
                    "emp_province": emp_province,
                    "date_of_birth": date_of_birth
                }

            # Make the API call ******************************************************************
            try:
                with_user = self.env['ir.config_parameter'].sudo()
                url = with_user.get_param('syncoria_can_payroll.base_url')
                if not url:
                    raise ValidationError(f"Failed to call the API, Need to configure a base url from the settings.")
                token = with_user.get_param('syncoria_can_payroll.token')
                header={
                    'Authorization': f'Token {token}'
                }
                response = requests.post(url, json=payload, headers=header)
                response_data = response.json()
                if 'FTAX' not in response_data:
                    print('response_data', response_data)
                    raise ValidationError(f"Failed to call the API: {response_data['detail'] if 'detail' in response_data else response_data['results']}")
                payslip.api_response_json = response_data
                payslip.api_payload_json = payload

            except Exception as e:
                raise ValidationError(f"{str(e)}")

            # Add FTAX and OTAX in Lines ************
            positive_amount_cat_list = ["GROSS", "ADD_ALLOWANCE", "ALW"]
            neg_amount_cat_list = ["DED", "PRE_TAX_DEDUCTION", "POST_TAX_DEDUCTION"]
            positive_amount = 0
            neg_amount = 0

            for x in pay_lines:
                category_code = self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).category_id.code
                if x['code'] == 'FTAX':
                    x['amount'] = response_data['FTAX'] if response_data else 0
                    x['total'] = response_data['FTAX'] if response_data else 0
                if x['code'] == 'OTAX':
                    x['amount'] = response_data['OTAX'] if response_data else 0
                    x['total'] = response_data['OTAX'] if response_data else 0

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

# this portion is for edit payslip line wizard *******************************
class HrPayrollEditPayslipLinesWizardInheritSynPayroll(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.lines.wizard'
    
    def recompute_following_lines(self, line_id):
        self.ensure_one()
        wizard_line = self.env['hr.payroll.edit.payslip.line'].browse(line_id)
        reload_wizard = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.edit.payslip.lines.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
        if not wizard_line.salary_rule_id:
            return reload_wizard
        localdict = self.payslip_id._get_localdict()
        rules_dict = localdict['rules']
        result_rules_dict = localdict['result_rules']
        remove_lines = False
        lines_to_remove = []
        blacklisted_rule_ids = []
        for line in sorted(self.line_ids, key=lambda x: x.sequence):
            if remove_lines and line.code in self.payslip_id.line_ids.mapped('code'):
                lines_to_remove.append((2, line.id, 0))
            else:
                rules_dict[line.code] = line.salary_rule_id
                if line == wizard_line:
                    line._compute_total()
                    remove_lines = True
                blacklisted_rule_ids.append(line.salary_rule_id.id)
                localdict[line.code] = line.total
                result_rules_dict[line.code] = {'total': line.total, 'amount': line.amount, 'quantity': line.quantity, 'rate': line.rate}
                localdict = line.salary_rule_id.category_id._sum_salary_rule_category(localdict, line.total)

        payslip = self.payslip_id.with_context(force_payslip_localdict=localdict, prevent_payslip_computation_line_ids=blacklisted_rule_ids)

        # Customised code start **********************************
        pay_lines =  payslip._get_payslip_lines()

        # api_payload_json update with onchange amount
        positive_amount = 0
        neg_amount = 0
        api_payload_json = self.payslip_id.api_payload_json
        if api_payload_json:
            if wizard_line.code == 'GROSS':
                api_payload_json['I'] = wizard_line.amount
                positive_amount = wizard_line.amount
            if wizard_line.code == 'RRSP':
                api_payload_json['F'] = wizard_line.amount
                neg_amount = wizard_line.amount
            if wizard_line.code == 'BONUS':
                api_payload_json['B'] = wizard_line.amount
                positive_amount = wizard_line.amount

            try:
                with_user = self.env['ir.config_parameter'].sudo()
                token = with_user.get_param('syncoria_can_payroll.token')
                url = with_user.get_param('syncoria_can_payroll.base_url')
                if not url:
                    raise ValidationError(f"Failed to call the API, need to configure a base url from the settings.")
                header = {
                    'Authorization': f'Token {token}'
                }
                response = requests.post(url, json=api_payload_json, headers=header)
                response_data = response.json()
                self.payslip_id.api_response_json = response_data
                self.payslip_id.api_payload_json = api_payload_json
                if 'FTAX' not in response_data:
                    raise ValidationError(f"Failed to call the API: {response_data['detail']}")

            except Exception as e:
                raise ValidationError(f"{str(e)}")

        # Add FTAX and OTAX in Lines ************
        positive_amount_cat_list = ["GROSS", "ADD_ALLOWANCE", "ALW"]
        neg_amount_cat_list = ["DED", "PRE_TAX_DEDUCTION", "POST_TAX_DEDUCTION"]

        for x in pay_lines:
            category_code = self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).category_id.code
            if x['code'] == 'FTAX':
                x['amount'] = response_data['FTAX'] if response_data else 0
                x['total'] = response_data['FTAX'] if response_data else 0
            if x['code'] == 'OTAX':
                x['amount'] = response_data['OTAX'] if response_data else 0
                x['total'] = response_data['OTAX'] if response_data else 0

            # add category wise amounts for net calculation ******************
            if category_code in positive_amount_cat_list:
                positive_amount += x['amount']
            elif category_code in neg_amount_cat_list:
                neg_amount += x['amount']

            # place the net amount
            if x['code'] == 'NET':
                x['amount'] = positive_amount - neg_amount
        # Customised code end **********************************

        self.line_ids = lines_to_remove + [(0, 0, line) for line in pay_lines]
        return reload_wizard