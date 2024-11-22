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

        rec = []
        for payslip in hr_payslip_run.slip_ids:
            rec.append((0,0,{
                "slip_id" : payslip.number,
                "employee_id": payslip.employee_id.id,
                "attendance_hours": payslip.worked_days_line_ids.filtered(lambda x: x.code == "WORK100").number_of_hours,
                "insurable_hour" :payslip.insurable_hour,
                "gross" :payslip.line_ids.filtered(lambda x: x.code == "GROSS").total,
                "vac_pay" :payslip.line_ids.filtered(lambda x: x.code == "VP").total,
                "insurable_earning":payslip.line_ids.filtered(lambda x: x.code == "I_Earning").total,
                "cpp" :payslip.line_ids.filtered(lambda x: x.code == "CPP").total,
                "cpp2" :payslip.line_ids.filtered(lambda x: x.code == "CPP2").total,
                "ei" :payslip.line_ids.filtered(lambda x: x.code == "EI").total,
                "e_cpp" :payslip.line_ids.filtered(lambda x: x.code == "CPP_EMPLOYER").total,
                "e_cpp2" :payslip.line_ids.filtered(lambda x: x.code == "CPP2_EMPLOYER").total,
                "e_ei" :payslip.line_ids.filtered(lambda x: x.code == "EI_EMPLOYER").total,
                "fed_tax" :payslip.line_ids.filtered(lambda x: x.code == "FTAX").total,
                "prov_tax" :payslip.line_ids.filtered(lambda x: x.code == "OTAX").total,
                "net":payslip.line_ids.filtered(lambda x: x.code == "NET").total,
                "acc_vac":payslip.line_ids.filtered(lambda x: x.code == "ACCRUED_VP").total,
            }))
        # return [(0,0,{"employee_id": employee.id}) for employee in self.env['hr.employee'].search(contract_domain)]
        return rec

    draft_line_ids = fields.One2many("hr.payslip.create.draft.line", 'manual_input_wizard_id', default=lambda self: self._get_payslips())

    def action_generate_draft_payslips(self):
        payslip_run_id = self._get_payslip_run_id()
        payslip_run_id.action_validate()




class SyncoriaCreateDraftLine(models.TransientModel):
    _name = "hr.payslip.create.draft.line"
    _description = "HR Payslip Create Draft Line"

    manual_input_wizard_id= fields.Many2one("hr.payslip.create.draft.wizard")
    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    slip_id = fields.Many2one("hr.payslip", string="Payslips")
    paycycle = fields.Char()

    attendance_hours = fields.Float(string="Attendance Hours")
    insurable_hour = fields.Float(string="Insurable Hour")
    gross = fields.Float(string="GROSS")
    vac_pay = fields.Float("Vacation Pay Amount")
    insurable_earning = fields.Float(string="Insurable Earning")
    cpp = fields.Float(string="CPP")
    cpp2 = fields.Float(string="CPP2")
    ei = fields.Float(string="EI")
    e_cpp = fields.Float(string="Employer CPP")
    e_cpp2 = fields.Float(string="Employer CPP2")
    e_ei = fields.Float(string="Employer EI")
    fed_tax = fields.Float(string="Federal Tax")
    prov_tax = fields.Float(string="Ontario Tax")
    net = fields.Float(string="Net Salary")
    acc_vac = fields.Float(string="Accrued Vacation")

