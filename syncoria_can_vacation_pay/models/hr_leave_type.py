from odoo import models,api,fields,_
class InheritedHrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.type'
    _description = 'InheritedHrLeaveAllocation'

    allow_vacation_pay = fields.Boolean("Allow vacation pay",default=False)

    def get_employees_days(self, employee_ids, date=None):
        res = super().get_employees_days(employee_ids, date)
        deductible_vacation_pay_time_off_type_ids = self.env['hr.leave.type'].search([
            ('allow_vacation_pay', '=', True),]).ids
        for employee_id, allocations in res.items():
            for allocation_id in allocations:
                if allocation_id in deductible_vacation_pay_time_off_type_ids:
                    virtual_remaining = res[employee_id][allocation_id]['virtual_remaining_leaves'] - self.env['hr.employee'].sudo().browse(
                        employee_id)._get_vacation_pay_calculation()
                    if virtual_remaining >0.0:
                        res[employee_id][allocation_id]['virtual_remaining_leaves'] = virtual_remaining
                    else:
                        res[employee_id][allocation_id]['virtual_remaining_leaves'] = 0.0

                    # res[employee_id][allocation_id]['overtime_deductible'] = True
                # else:
                #     res[employee_id][allocation_id]['overtime_deductible'] = False
        return res

