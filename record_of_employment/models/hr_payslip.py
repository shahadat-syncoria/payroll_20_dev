from odoo import fields, models, api, _


class InsurablePayslip(models.Model):
    _inherit = 'hr.payslip'

    insurable_hour = fields.Float(string="Insurable Hour")
    roe_id = fields.Many2one("record.of.employee", string="Roe")

    insurable_earning = fields.Float(string="Insurable Earning")

    def get_insurable_earning(self):
        amount = 0.0
        for line in self.line_ids:
            if line.code == "I_Earning":
                amount = line.amount
        return amount

    def get_insurable_hour(self):
        vacation_amount = 0.0
        timesheet_amount = 0.0
        vacation_pay_req = self.env['hr.vacation.pay']

        # vacation_amount = sum(self.input_line_ids.filtered(lambda x: x.code=="Vacation_pay" ).amount)
        # timesheet_amount = self.worked_days_line_ids.filtered(lambda x: x.number_of_hours if x.work_entry_type_id.code=="TIMESHEET_WORK100" else 0.0)

        for input_line in self.input_line_ids:
            if input_line.code == "Vacation_Pay":
                vacation_pay_req_ids = input_line.vacation_pay_req_ref.split(
                    ',') if input_line.vacation_pay_req_ref else []

                for vpr in vacation_pay_req_ids:
                    vpr_id = vacation_pay_req.search([('name', '=', vpr)], limit=1)
                    if vpr_id:
                        vacation_amount += (vpr_id.duration*self.contract_id.resource_calendar_id.hours_per_day)
        for work_entry in self.worked_days_line_ids:
            if work_entry.work_entry_type_id.code == "TIMESHEET_WORK100" and self.contract_id.work_entry_source == 'timesheet_hours':
                timesheet_amount += work_entry.number_of_hours
            elif work_entry.work_entry_type_id.code == "WORK100":
                timesheet_amount += work_entry.number_of_hours
        result = vacation_amount + timesheet_amount

        return result

    def compute_sheet(self):
        for rec in self:
            rec.write({
                "insurable_hour": rec.get_insurable_hour(),
                "insurable_earning": rec.get_insurable_earning()
            })
        res = super(InsurablePayslip, self).compute_sheet()
        return res
