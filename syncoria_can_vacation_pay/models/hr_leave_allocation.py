from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo.http import request


class InheritedHrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for rec in vals_list:
    #         vacation_pay_time_off_type_id = self.env['hr.work.entry.type'].search([
    #             ('allow_vacation_pay', '=', True)], limit=1)
    #         if vacation_pay_time_off_type_id and request.params['model'] != 'ir.cron':
    #             if rec.get('work_entry_type_id') == vacation_pay_time_off_type_id.id:
    #                 raise UserError("You can not allocate vacation pay manually!!")
    #     return super(InheritedHrLeaveAllocation,self).create(vals_list)

    def action_allocation_vac_leave(self):
        """
         Employees who have leave type containing allow_vacation_pay True will be searched.
         If the employee already have an allocation then it will update the number of days .
         If no allocation is found then it will create a new allocation.

        """
        if self.env["ir.config_parameter"].sudo().get_str('syncoria_can_vacation_pay.vac_pay_type') == 'time_wise':
            today = fields.Date.context_today(self)
            # v20: employees with a currently running contract (hr.version with contract dates covering today)
            contract_domain = [('version_ids', 'any', [
                                   ('contract_date_start', '!=', False),
                                   ('contract_date_start', '<=', today),
                                   '|', ('contract_date_end', '=', False),
                                   ('contract_date_end', '>=', today),
                               ]),
                               ('company_id', '=', self.env.company.id),
                               ]
            employees = self.env['hr.employee'].search(contract_domain)
            vacation_pay_time_off_type_id = self.env['hr.work.entry.type'].search([
                ('allow_vacation_pay', '=', True), ], limit=1)
            if not vacation_pay_time_off_type_id:
                raise UserError(_("Not vacation Type set!"))

            for employee in employees:
                try:
                    employee._get_employee_allocated_leave()

                    previous_allocated_vac_id = self.search([
                        ('work_entry_type_id', '=', vacation_pay_time_off_type_id.id),
                        ('employee_id', '=', employee.id), ('state', '=', 'validate')
                    ], limit=1)
                    allocated_day = round(employee.allocated_vacation_leave, 2) - (previous_allocated_vac_id.number_of_days or 0.0)
                    if allocated_day > 0.0:

                        if previous_allocated_vac_id:
                            # Update

                            previous_allocated_vac_id.action_refuse()
                            # previous_allocated_vac_id.action_draft()
                            previous_allocated_vac_id["number_of_days"] += allocated_day
                            previous_allocated_vac_id.action_approve()
                            previous_allocated_vac_id.message_post(
                                body=f"Vacation Leave for {employee.name} \n {datetime.today().date().__str__()}\n Allocation: {allocated_day}")

                        else:
                            # create
                            data = {
                                'name': f'Vacation Leave for {employee.name}',
                                'work_entry_type_id': vacation_pay_time_off_type_id.id,
                                'number_of_days': allocated_day,
                                'employee_id': employee.id,
                                # 'state': 'validate',
                                'date_from': datetime.today().date(),
                                # 'date_to': datetime(datetime.today().year,12,31).date(),
                            }
                            record = self.sudo().create(data)
                            # allocation is auto-approved on create when the type needs no validation
                            if record.state != 'validate':
                                record.action_approve()
                            record.message_post(
                                body=f"Vacation Leave for {employee.name} \n {datetime.today().date().__str__()}\n Allocation: {allocated_day}")
                except Exception as e:
                    employee.message_post(
                        body=f"Vacation Pay allocation failed.\n Number of days: {employee.allocated_vacation_leave}\n Date: {datetime.today()}\n Error: {e}")

    def action_delete_validate(self):
        for rec in self:
            rec.action_refuse()
            # rec.action_draft()
            rec.unlink()
