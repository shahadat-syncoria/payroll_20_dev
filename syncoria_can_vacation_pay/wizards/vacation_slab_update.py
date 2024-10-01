from odoo import models, fields, api

class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = 'Vacation Slab Wizard'

    message = fields.Text(string='Message')

    @api.model
    def default_get(self, fields):
        defaults = super(MessageWizard, self).default_get(fields)

        # Retrieve the active IDs from the context
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            # Fetch the employee records based on the active_ids
            employee_records = self.env['hr.employee'].search([('id', 'in', active_ids)])

            # Initialize a list to store names of employees whose vacation_slab_ids length is greater than 0
            employee_names_with_slabs = []
            employees_with_slabs = []

            for employee in employee_records:
                # Check if the length of vacation_slab_ids is greater than or equal to 1
                if len(employee.vacation_slab_ids) > 0:
                    employee_names_with_slabs.append(employee.name)
                else:
                    employees_with_slabs.append(employee.name)

            # Only set the message if there are employees with non-empty vacation slabs
            if employee_names_with_slabs:
                defaults['message'] = 'The vacation slabs of the following employees will be overwritten:\n' + '\n'.join(employee_names_with_slabs)
            else:
                defaults['message'] = 'The vacation slabs will be updated for:\n' + '\n'.join(employees_with_slabs)
        else:
            defaults['message'] = 'No active records found.'

        return defaults

    def action_confirm(self):
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            # Fetch the employee records based on the active_ids
            employee_records = self.env['hr.employee'].search([('id', 'in', active_ids)])

            for employee in employee_records:
                employee.update_vacation_slab()