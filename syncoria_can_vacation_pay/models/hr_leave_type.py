from odoo import models,api,fields,_
class SyncoriaInheritedHrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.type'
    _description = 'InheritedHrLeaveAllocation'

    allow_vacation_pay = fields.Boolean("Allow vacation pay",default=False)

    def get_allocation_data(self, employees, target_date=None):
        res = super(SyncoriaInheritedHrLeaveAllocation,self).get_allocation_data(employees, target_date)
        deductible_vacation_pay_time_off_type_ids = self.env['hr.leave.type'].search([
            ('allow_vacation_pay', '=', True),]).ids
        #[FIX: chceck employee]
        for employee_id, allocations in res.items():
            for allocation_id in allocations:
                if allocation_id[3] in deductible_vacation_pay_time_off_type_ids:
                    virtual_remaining = allocation_id[1]['virtual_remaining_leaves'] - self.env['hr.employee'].sudo().browse(
                        employee_id.id)._get_vacation_pay_calculation()
                    if virtual_remaining >0.0:
                        allocation_id[1]['virtual_remaining_leaves'] = virtual_remaining
                    else:
                        allocation_id[1]['virtual_remaining_leaves'] = 0.0

                    # res[employee_id][allocation_id]['overtime_deductible'] = True
                # else:
                #     res[employee_id][allocation_id]['overtime_deductible'] = False
        return res

