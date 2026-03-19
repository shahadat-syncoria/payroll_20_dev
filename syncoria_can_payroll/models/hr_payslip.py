import requests
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from odoo import api, models, _
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime
from ..helper.helper_functions import year_selection
from collections import defaultdict, Counter



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

    pay_cycle = fields.Many2one('paycycle.config', related='version_id.salary_pay_cycle', readonly=True)
    pay_cycle_period = fields.Many2one('paycycle.period')
    pay_cycle_period_ids_domain = fields.Binary(
        compute='_compute_pay_cycle_period_domain', readonly=True,
        store=False)
    is_manual_input = fields.Boolean(compute='_compute_is_manual_input')

    irre_amount = fields.Float("Irregular Amount",default=0)
    api_response_json = fields.Json()
    api_payload_json = fields.Json()
    year = fields.Selection(
        year_selection,
        string="Year",
        default=lambda self: str(datetime.now().year)
    )
    #====================need to remove=====================
    irre_fed_tax = fields.Float("Irregular Fed Tax",default=0)
    irre_prov_tax = fields.Float("Irregular Prov Tax",default=0)
    # ==============================================================
    fed_tax = fields.Float("Fed Tax",default=0)
    prov_tax = fields.Float("Prov Tax",default=0)


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
                    'year' :slip.payslip_run_id.pay_cycle_year,
                    'pay_cycle_period': slip.payslip_run_id.pay_cycle_period if slip.payslip_run_id.pay_cycle_period else slip.pay_cycle_period,
                })

    # ======================================================

    @api.depends('pay_cycle','year')
    def _compute_pay_cycle_period_domain(self):
        for rec in self:
            rec.pay_cycle_period_ids_domain = False
            if rec.pay_cycle:
                pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_year_slab_ids.filtered(lambda x: x.year == str(rec.year)).paycycle_period_ids.ids
                # pay_cycle_period_ids_domain = rec.pay_cycle.paycycle_period_ids.filtered(
                #     lambda x: x.paycycle_config_id.id == rec.pay_cycle.id and x.paycycle_year_slab_id.year == str(rec.year)).ids
                rec.pay_cycle_period_ids_domain = pay_cycle_period_ids_domain

    @api.onchange('year')
    def _onchange_year(self):
        for rec in self:
            rec.pay_cycle_period = None

    @api.onchange('pay_cycle_period')
    def _onchange_pay_cycle_period(self):
        for rec in self:
            if rec.pay_cycle_period:
                rec.write({
                    'name': rec.pay_cycle_period.name + f'-{rec.year}',
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
                    'year':rec.payslip_run_id.pay_cycle_year,
                    'pay_cycle_period': rec.payslip_run_id.pay_cycle_period,
                })

    def action_payslip_paid(self):
        if any(slip.state not in ['validated'] for slip in self):
            raise UserError(_('Cannot mark payslip as paid if not confirmed or waiting.'))
        self.write({'state': 'paid', 'paid_date': fields.Date.today()})
        # ================= YTD Information Update =========
        # for slip in self:
        #     slip.employee_id.with_context({"type":"ALL"}).update_ytd_erp() # "ALL" is for update YTD of CPP,CPP2,PI
        #     slip.employee_id.update_ytd_irregular_payments_tax() # "ALL" is for update YTD of CPP,CPP2,PI

    def action_payslip_cancel(self):
        super(InheritedHrPayslip,self).action_payslip_cancel()
        for slip in self:
            slip.employee_id.with_context({"type":"ALL", "year": slip.date_to.year, "action": 'cancel'}).update_ytd_erp() # "ALL" is for update YTD of CPP,CPP2,PI
            # slip.employee_id.update_ytd_tax(slip.date_to.year) # "ALL" is for update YTD of CPP,CPP2,PI

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
                # rec.employee_id.with_context({"type": "ALL"}).update_ytd_erp()
                rec.write({
                    'irre_amount': sum([line.amount for line in rec.line_ids if line.salary_rule_id.is_irregular_payment]),
                     'fed_tax': sum([line.amount for line in rec.line_ids if line.code=='FTAX']),
                     'prov_tax': sum([line.amount for line in rec.line_ids if line.code=='OTAX'])
                })
                rec.employee_id.with_context({"type": "ALL", "year": rec.date_to.year, "action": 'paid'}).update_ytd_erp()
                # rec.employee_id.update_ytd_tax(rec.date_to.year)
        return res

    @api.depends('employee_id.current_version_id', 'version_id.last_modified_date', 'date_from')
    def _compute_is_wrong_version(self):
       pass
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
            is_pay_cycle = rec.version_id.salary_pay_cycle.pay_cycle
            gross_work_entry_type = self.env['hr.work.entry.type'].search([('is_gross', '=',True)])
            deduct_from_gross_work_entry_type = self.env['hr.work.entry.type'].search([('deduct_from_gross', '=',True)])
            result += sum([round(rec._get_worked_days_line_values_orm(gross_entry_type.code),2) if gross_entry_type.code else 0.0 for gross_entry_type in gross_work_entry_type])
            result -= sum([abs(round(rec._get_worked_days_line_values_orm(deduct_gross_entry_type.code),2)) if deduct_gross_entry_type.code else 0.0 for deduct_gross_entry_type in deduct_from_gross_work_entry_type])
            if is_pay_cycle and not rec.version_id.is_hourly:
                if rec.version_id.work_entry_source in ['attendance','calendar']:
                    result += round(rec._get_worked_days_line_values_orm('WORK100'),2)
                elif rec.version_id.work_entry_source == 'timesheet_hours':
                    result += round(rec._get_worked_days_line_values_orm('TIMESHEET_WORK100'),2)
            elif is_pay_cycle and rec.version_id.is_hourly:
                if rec.version_id.work_entry_source in ['attendance','calendar']:
                    result += round(rec._get_worked_days_line_values_orm('WORK100'),2)
                elif rec.version_id.work_entry_source == 'timesheet_hours':
                    result += round(rec._get_worked_days_line_values_orm('TIMESHEET_WORK100'),2)
                else:
                    result = 0.0
            else:
                result = 0.0
        except:
            pass

        return result

    def _get_new_worked_days_lines(self):

        res = super()._get_new_worked_days_lines()
        unpaid_work_entry = self.env["hr.work.entry.type"].search([("is_leave","=",True),("is_negative_amount","=", True)]).ids
        avg_working_hour_per_day = self.version_id.resource_calendar_id.hours_per_day
        new_worked_days_lines = []
        for entry in res:
            entry_data = entry[2]
            if entry_data['work_entry_type_id'] in unpaid_work_entry:
                unpaid_hour = -entry_data['number_of_hours']
                entry_data['number_of_hours'] = unpaid_hour
                entry_data['number_of_days'] = unpaid_hour / avg_working_hour_per_day
            new_worked_days_lines.append(entry)
        res = new_worked_days_lines

        return res

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

            attendance_type_id = self.env.ref('hr_work_entry.work_entry_type_attendance').id

            existing_line = rec.worked_days_line_ids.filtered(
                lambda l: l.work_entry_type_id.id == attendance_type_id
            )

            vac_pay = manual_input_line_id.vac_pay
            bonus = manual_input_line_id.bonus
            commission = manual_input_line_id.commission
            retro = manual_input_line_id.retro
            avg_working_hour_per_day = rec.version_id.resource_calendar_id.hours_per_day
            # rec.worked_days_line_ids.unlink()
            # rec.input_line_ids.unlink()
            worked_days_lines = []
            if attendance_hour > 0.0 and rec.version_id.work_entry_source in ["calendar","attendance"] :
                if existing_line:
                    existing_line.write({
                        'number_of_days': attendance_hour / avg_working_hour_per_day,
                        'number_of_hours': attendance_hour,
                        'name': 'Attendance',
                    })
                else:
                    rec.write({
                        'worked_days_line_ids': [(0, 0, {
                            'work_entry_type_id': attendance_type_id,
                            'name': 'Attendance',
                            'number_of_days': attendance_hour / avg_working_hour_per_day,
                            'number_of_hours': attendance_hour,
                        })]
                    })

            # if over_time_hour > 0.0:
            #     worked_days_lines.append((0, 0, {
            #         'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_overtime_work_entry_type').id,
            #         'name': 'Overtime',
            #         'number_of_days': over_time_hour / avg_working_hour_per_day,
            #         'number_of_hours': over_time_hour,
            #         # 'amount': timesheet_hours*payslip.version_id.hourly_wage
            #
            #     }))
            # if stat_over_time_hour > 0.0:
            #     worked_days_lines.append((0, 0, {
            #         'work_entry_type_id': self.env.ref('syncoria_can_overtime.sync_stat_overtime_work_entry_type').id,
            #         'name': 'Statutory Holidays Overtime',
            #         'number_of_days': stat_over_time_hour / avg_working_hour_per_day,
            #         'number_of_hours': stat_over_time_hour,
            #         # 'amount': timesheet_hours*payslip.version_id.hourly_wage
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
            if slip.version_id and (slip.date_from < slip.version_id.date_start
                                     or (slip.version_id.date_end and slip.date_to > slip.version_id.date_end)):
                warnings.append(_("The period selected does not match the contract validity period."))

            if slip.date_to > date_utils.end_of(fields.Date.today(), 'month'):
                warnings.append(_(
                    "Work entries may not be generated for the period from %(start)s to %(end)s.",
                    start=date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1),
                    end=slip.date_to,
                ))

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
        if not self.state in ('validated', 'done', 'paid'):
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
#==================================FOR v18 ytd computation========================
    def _get_last_ytd_payslips(self):
        res = super(InheritedHrPayslip, self)._get_last_ytd_payslips()
        if not self:
            return self

        earliest_date_to = min(self.mapped('date_to'))
        earliest_ytd_date_to = min(
            company.get_last_ytd_reset_date(earliest_date_to) for company in self.company_id
        )
        ytd_payslips_grouped = self.env['hr.payslip']._read_group(
            domain=[
                ('employee_id', 'in', self.employee_id.ids),
                ('struct_id', 'in', self.struct_id.ids),
                ('ytd_computation', '=', True),
                ('date_to', '>=', earliest_ytd_date_to),
                ('date_to', '<=', max(self.mapped('date_to'))),
                ('state', 'in', ['paid']),
            ],
            groupby=['employee_id', 'struct_id'],
            aggregates=['id:recordset']
        )

        ytd_payslips_sorted = defaultdict(lambda: self.env['hr.payslip'])
        for employee_id, struct_id, payslips in ytd_payslips_grouped:
            ytd_payslips_sorted[(employee_id, struct_id)] = payslips.sorted(
                key=lambda p: p.date_to, reverse=True
            )

        last_ytd_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            last_payslips = ytd_payslips_sorted[(payslip.employee_id, payslip.struct_id)].filtered(
                lambda p: p.date_to <= payslip.date_to
            )
            if last_payslips and last_payslips[0].date_to >= \
                    payslip.company_id.get_last_ytd_reset_date(payslip.date_to):
                last_ytd_payslips[payslip] = last_payslips[0]

        return res

    def _payslip_line_ytd_total(self):
        self.ensure_one()

        line_ids = self.employee_id._get_ytd_payslip_line_ids(self.year)

        rules = self.employee_id.version_id.structure_type_id.default_struct_id.rule_ids

        opening_rec = self.env['hr.payslip.ytd.opening'].search([
            ('employee_id', '=', self.employee_id.id),
            ('year', '=', self.year),
            ('version_id', '=', self.version_id.id),
            ('company_id', '=', self.company_id.id),
        ], limit=1)


        opening_dict = {}
        if opening_rec:
            for line in opening_rec.ytd_opening_lines:
                opening_dict[line.salary_rule_id.code] = line.opening_amount


        ytd_totals = {}
        for rule in rules:
            payslip_total = sum(line.total for line in line_ids if line.salary_rule_id.id == rule.id)
            opening_total = opening_dict.get(rule.code, 0.0)
            ytd_totals[rule.code] = round(payslip_total + opening_total, 2)

        return ytd_totals

    def _get_payslip_lines(self):
        # Call original method to get line values
        line_vals = super()._get_payslip_lines()

        # Get YTD totals for this payslip
        ytd_dict = self._payslip_line_ytd_total()

        # Add YTD amount to each line if rule code exists
        for line in line_vals:
            code = line.get('code')
            line['ytd'] = ytd_dict.get(code, 0.0)

        return line_vals

    def action_payslip_refresh(self):
        for x in self:
            x._onchange_pay_cycle_period()
            x.compute_sheet()

    # inherited compute_sheet method for tax api call
    def compute_sheet(self):
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'validated'])
        payslips.line_ids.unlink()
        self.env.flush_all()
        today = fields.Date.today()

        for payslip in payslips:
            ytd_dict = payslip._payslip_line_ytd_total()
            emp_line_obj = payslip.employee_id.payroll_line_ids.filtered(lambda x: x.year == str(payslip.date_to.year))
            # number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            payslip.write({
                # 'number': number,
                'state': 'validated',
                'compute_date': today
            })

            # Customised code start *****************************************************
            # API endpoint
            pay_lines = payslip._get_payslip_lines()
            I = 0
            F = 0
            Emp_F = 0
            B = 0
            V = 0
            PI = 0
            IE = 0
            V_list = ['ADJUST_VP','VP']
            for x in pay_lines:
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).is_irregular_payment:
                    B += x['amount']
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).is_pensionable:
                    PI += x['amount']
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).is_insurable_earning:
                    IE += x['amount']
                if self.env['hr.salary.rule'].sudo().browse(x['salary_rule_id']).category_id.code == "GROSS":
                    I += x['amount']
                if x['code'] in V_list:
                    V += x['amount']
                if x['code'] == 'RRSP':
                    F = x['amount']
                if x['code'] == 'RRSP_EMPLOYER':
                    Emp_F = x['amount']
            # Parameters for the API request
            P = payslip.pay_cycle.pay_cycle
            D = emp_line_obj.ytd_cpp
            D1 = emp_line_obj.ytd_ei
            D2 = emp_line_obj.ytd_cpp2
            ytd_pi = emp_line_obj.ytd_pi
            emp_province = payslip.employee_id.territory_of_employment.code
            B1 = emp_line_obj.year_to_date_irregular_payment
            federal_amount_from_td1 = payslip.version_id.federal_amount_from_td1
            proviancial_amount_from_td1 = payslip.version_id.proviancial_amount_from_td1
            date_of_birth = str(payslip.employee_id.birthday)
            amount_withdraw = payslip.version_id.rrsp_amount_withdraw
            if date_of_birth == 'False':
                raise ValidationError("Employee Date of Birth Mandatory")
            payroll_year = payslip.date_to.year
            payload = {
                    "I": I,
                    "P": P,
                    "B": B,
                    "PI":PI,
                    "IE":IE,
                    "B1": B1,
                    "D": D,
                    "F": F,
                    "Emp_F": Emp_F,
                    "F1": 0,
                    "F2": 0,
                    "F3": 0,
                    "F4": 0,
                    "D1": D1,
                    "D2": D2,
                    "YTD_PI": ytd_pi,
                    "TC": federal_amount_from_td1,
                    "TCP": proviancial_amount_from_td1,
                    "amount_withdraw" : amount_withdraw,
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
            payslip.message_post(
                body=f"{payload}",

            )

            # Make the API call ******************************************************************
            try:
                with_user = self.env['ir.config_parameter'].sudo()
                url = with_user.get_param('syncoria_can_payroll.base_url')
                if not url:
                    raise ValidationError(f"Failed to call the API, Need to configure a base url from the settings.")

                # Remove everything after port 8000
                split_url = urlsplit(url)
                if split_url.port == 8000:
                    new_netloc = split_url.hostname + (f":{split_url.port}" if split_url.port else "")
                else:
                    new_netloc = split_url.netloc
                # Create a new URL without modifying other components
                final_url = urlunsplit((split_url.scheme, new_netloc, '', '', ''))

                end_point = '/api/v1/payroll_info/calculate-tax/'
                token = with_user.get_param('syncoria_can_payroll.token')
                header={
                    'Authorization': f'Token {token}'
                }
                response = requests.post(final_url+end_point, json=payload, headers=header)
                response_data = response.json()
                payslip.message_post(
                    body=f"{response_data}",

                )
                if 'FTAX' not in response_data:
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
                # update data from api to payslip lines
                if x['code'] == 'FTAX':
                    ftax = response_data['FTAX'] if response_data else 0
                    x['amount'], x['total'] = ftax, ftax

                if x['code'] == 'OTAX':
                    otax  = response_data['OTAX'] if response_data else 0
                    x['amount'], x['total'] = otax, otax

                if x['code'] in ['CPP', 'CPP_EMPLOYER']:
                    cpp = response_data['CPP'] if response_data else 0
                    x['amount'], x['total'] = cpp, cpp

                if x['code'] in ['CPP2', 'CPP2_EMPLOYER']:
                    cpp2  = response_data['CPP2'] if response_data else 0
                    x['amount'], x['total'] = cpp2, cpp2

                if x['code'] == 'EI':
                    ei  = response_data['EI'] if response_data else 0
                    x['amount'], x['total'] = ei, ei

                if x['code'] == 'EI_EMPLOYER':
                    emp_ei  = response_data['EI_EMPLOYER'] if response_data else 0
                    x['amount'], x['total'] = emp_ei, emp_ei

                # validated whether cpp and ei exempt are enabled, and if so, set them to 0 respectively.
                if payslip.employee_id.is_cpp_exempt and x['code'] in ['CPP','CPP2','CPP_EMPLOYER','CPP2_EMPLOYER']:
                    x['amount'], x['total'] = 0,0

                if payslip.employee_id.is_ei_exempt and x['code'] in ['EI','EI_EMPLOYER']:
                    x['amount'], x['total'] = 0,0

                # add category wise amounts for net calculation ******************
                if category_code in positive_amount_cat_list:
                    positive_amount += round(x['amount'], 2)
                elif category_code in neg_amount_cat_list:
                    neg_amount += round(x['amount'], 2)

                # place the net amount
                if x['code'] == 'NET':
                    net_amount = round(positive_amount - neg_amount, 2)
                    x['amount'] = net_amount
                    x['total'] = net_amount

                # code = x.get('code')
                # x['ytd'] = ytd_dict.get(code, 0.0) + x['total']

            self.env['hr.payslip.line'].create(pay_lines)
        return True

