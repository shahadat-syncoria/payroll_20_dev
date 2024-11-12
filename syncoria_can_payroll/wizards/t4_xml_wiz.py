import datetime

from odoo import models, fields, api

class MessageWizard(models.TransientModel):
    _name = 't4.messeage.wizard'
    _description = 'T4 Batch XML Wizard'

    message = fields.Text(string='Message')

    @api.model
    def default_get(self, fields):
        defaults = super(MessageWizard, self).default_get(fields)

        # Retrieve the active IDs from the context
        active_ids = self.env.context.get('active_ids', [])

        if active_ids:
            # Fetch the employee records based on the active_ids
            employee_records = self.env['statement.remuneration'].search([('id', 'in', active_ids)])


            employee_done = []
            employees_not_done = []

            for employee in employee_records:

                if employee.state == 'done':
                    employee_done.append(employee.employee_id.name)
                else:
                    employees_not_done.append(employee.employee_id.name)


            if employee_done:
                defaults['message'] = 'T4 XML will be generated for:\n' + '\n'.join(employee_done) + '\n\nYou need to change the state to done for these employees to create T4 XML:\n' + '\n'.join(employees_not_done)
            else:
                defaults['message'] = 'No active records found.'

        return defaults

    def action_confirm(self):
        # Generate the T4 XML content
        kwrgs = []
        domain = []
        if self.env.context.get('active_ids'):
            domain = [('id', 'in', self.env.context.get('active_ids', [])),('state','=','done')]
            employees = self.env["statement.remuneration"].search(domain)
            employee = self.env["statement.remuneration"].search([('id', '=', self.env.context.get('active_id'))])
            filename = 'Merged T4' + str(datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")) + '.xml'

        # for rec in self:
        xml_content = employee.generate_t4_xml(employees)
        employee.xml_content = xml_content
        print(xml_content)

        # Prepare the file for download
        # filename = f'{rec.employee_id.name}' + '_T4' + '.xml'

        content_type = 'application/xml'

        kwrgs.append((xml_content, filename, content_type))

        # Return the file as a response
        return {
            'type': 'ir.actions.act_url',
            'url': '/t4/download_xml?field=xml_content&id=%s&filename=%s&content_type=%s' % (
                employee.id, filename, content_type),
            'target': 'self',
        }

