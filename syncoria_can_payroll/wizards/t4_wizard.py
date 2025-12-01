from odoo import models, fields, api
from ..helper.helper_functions import year_selection


class TestWizard(models.TransientModel):
    _name = 'statement.remuneration.wizard'
    _description = "Statement Remuneration Wizard"



    def _get_employee_domain(self):
        return [('company_id','in', self.env.company.ids)]



    employee_ids = fields.Many2many('hr.employee',string="Employee")
    department_ids = fields.Many2many('hr.department',string='Department',)
    year = fields.Selection(
        year_selection,
        string="Year",
        store=True,
        default='2023'
    )


    def default_get(self, fields):
        defaults = super(TestWizard, self).default_get(fields)

        # Retrieve the active IDs from the context
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            employee = self.env["hr.employee"].search([("id", "in", active_ids)])
            # Set the employee_ids field with the active employee records

            defaults['employee_ids'] = [(6, 0,employee.ids)]


        return defaults



            # Initialize a list to store names of employees whose vacation_slab_ids length is greater than 0
            # employee_names_with_slabs = []
            # employees_with_slabs = []

            # for employee in employee_records:
            #     print(employee.name)
        #         # Check if the length of vacation_slab_ids is greater than or equal to 1
        #         if len(employee.vacation_slab_ids) > 0:
        #             employee_names_with_slabs.append(employee.name)
        #         else:
        #             employees_with_slabs.append(employee.name)
        #
        #     # Only set the message if there are employees with non-empty vacation slabs
        #     if employee_names_with_slabs:
        #         defaults[
        #             'message'] = 'The vacation slabs of the following employees will be overwritten:\n' + '\n'.join(
        #             employee_names_with_slabs)
        #     else:
        #         defaults['message'] = 'The vacation slabs will be updated for:\n' + '\n'.join(employees_with_slabs)
        # else:
        #     defaults['message'] = 'No active records found.'



    # @api.onchange('department_ids')
    # def _onchage_deperatment(self):
    #     self.ensure_one()
    #     domain = [('department_id', 'child_of', self.department_ids.ids)]
    #     domain += [('version_id','!=',False)]
    #     dep_wise_employee = self.env['hr.employee'].search(domain)
    #     if self.department_ids:
    #         # self.employee_ids = [(6, 0, [])]
    #         # employee_line_list = [(0, 0, {
    #         #     'id': employee_id.id,
    #         # }) for employee_id in dep_wise_employee]
    #
    #         self.employee_ids = [(6,0,[employee_id.id for employee_id in dep_wise_employee])]
    #     else:
    #         if self.employee_ids:
    #             self.employee_ids=[(6, 0, [])]


    def generate_t4_records(self):
        self.ensure_one()
        statement_remuneration = self.env['statement.remuneration']
        for employee in self.employee_ids:


            exist_statement_remuneration = statement_remuneration.search([('employee_id','=',employee.id),('year','=',self.year)],limit=1)
            if exist_statement_remuneration:
                exist_statement_remuneration.compute_t4()
            else:
                try:
                    # employee_contract = employee.contract_ids.filtered_domain([('state','=','open')])
                    if employee.version_id:
                        values = {
                            'employee_id': employee.id,
                            'year':self.year,
                            'employee_contract':employee.version_id.id

                        }
                        record = statement_remuneration.create(values)
                        record.compute_t4()
                        record.write({
                            'state': 'done'
                        })
                except:
                    pass





        return {
            'type': 'ir.actions.act_window',
            'res_model': 'statement.remuneration',
            'view_mode': 'list,form',
            'target': 'self',
            'name': "T4 Form Slip",
            # 'domain': [('id', 'in', self.purchase_order_line_ids.mapped('order_id').ids)],
            # 'context': {
            #     'quotation_only': True,
            # }
        }



