from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class SyncoriaCreateDraftWizard(models.TransientModel):
    _name = "hr.payslip.create.draft.wizard"
    _description = "HR Employee Create Draft Wizard"
    @api.model
    def _get_default_attendance_hours(self,hr_payslip_run,employee_id):
        if not employee_id.contract_id.is_hourly:
            return (hr_payslip_run.date_end - hr_payslip_run.date_start).days *employee_id.contract_id.standard_calendar_id.hours_per_day
        else:
            return 0.0

    def _get_payslip_run_id(self):
        context = self.env.context
        if 'active_model' in context and context.get('active_model') == 'hr.payslip.run':
            hr_payslip_run = self.env['hr.payslip.run'].browse(context.get('active_id'))
            return hr_payslip_run


    def _get_payslips(self):

        hr_payslip_run = self._get_payslip_run_id()
        vac_pay = self.env.ref('syncoria_can_vacation_pay.input_ca_vac_pay')
        commission = self.env.ref('syncoria_can_irregular_payment.input_ca_commission')
        bonus = self.env.ref('syncoria_can_irregular_payment.input_ca_bonus_pay')
        retro = self.env.ref('syncoria_can_irregular_payment.input_ca_retro_pay')
        rec = []
        for payslip in hr_payslip_run.slip_ids:
            rec.append((0,0,{
                "slip_id" : payslip.id,
                "employee_id": payslip.employee_id.id,
                "attendance_hours": payslip.worked_days_line_ids.filtered(lambda x: x.code == "WORK100").number_of_hours,
                "overtime_hours" : payslip.worked_days_line_ids.filtered(lambda x: x.code == "CAN_OVERTIME").number_of_hours,
                "stat_overtime_hours" : payslip.worked_days_line_ids.filtered(lambda x: x.code == "CAN_STAT_OVERTIME").number_of_hours,
                "payout_vacation_pay_paycycle":True if payslip.payout_vacation_pay_paycycle else False,
                "ytd_vac_pay_amount" : payslip.ytd_vac_pay_amount,
                "vac_pay" : payslip.input_line_ids.filtered(lambda x: x.code == vac_pay.code).amount,
                "commission" : payslip.input_line_ids.filtered(lambda x: x.code == commission.code).amount,
                "bonus" : payslip.input_line_ids.filtered(lambda x: x.code == bonus.code).amount,
                "retro" : payslip.input_line_ids.filtered(lambda x: x.code == retro.code).amount,
            }))
        # return [(0,0,{"employee_id": employee.id}) for employee in self.env['hr.employee'].search(contract_domain)]
        return rec

    draft_line_ids = fields.One2many("hr.employee.manual.input.line", 'create_draft_id', default=lambda self: self._get_payslips())

    def action_generate_draft_payslips(self):
        payslip_run_id = self._get_payslip_run_id()
        for payslip in payslip_run_id.slip_ids:
            payslip
        payslip_run_id.action_validate()

    def compute_sheet(self):

        payslip_run_id = self._get_payslip_run_id()

        # Recompute the entire payslip run if needed
        for payslip in payslip_run_id.slip_ids:
            payslip.compute_workdays_manual_input(self.draft_line_ids)
            payslip.compute_sheet()







