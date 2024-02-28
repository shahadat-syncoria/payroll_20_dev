import os
import base64
import urllib

import werkzeug

from odoo import models, fields, api
from ..helper.helper_functions import year_selection


class TestWizard(models.TransientModel):
    _name = 'statement.remuneration.wizard'
    _description = "Statement Remuneration Wizard"



    def _get_employee_domain(self):
        return [('company_id','in', self.env.company.ids)]

    employee_ids = fields.Many2many('hr.employee',store=True, string="Employee", domain=lambda self: self._get_employee_domain())
    department_ids = fields.Many2many('hr.department',string='Department', domain=lambda self: self._get_employee_domain())
    year = fields.Selection(
        year_selection,
        string="Year",
        store=True,
        default='2023'
    )

    @api.onchange('department_ids')
    def _onchage_deperatment(self):
        self.ensure_one()
        domain = [('department_id', 'child_of', self.department_ids.ids)]
        domain += [('contract_id','!=',False)]
        dep_wise_employee = self.env['hr.employee'].search(domain)
        if self.department_ids:
            # self.employee_ids = [(6, 0, [])]
            # employee_line_list = [(0, 0, {
            #     'id': employee_id.id,
            # }) for employee_id in dep_wise_employee]

            self.employee_ids = [(6,0,[employee_id.id for employee_id in dep_wise_employee])]
        else:
            if self.employee_ids:
                self.employee_ids=[(6, 0, [])]


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
                    if employee.contract_id:
                        values = {
                            'employee_id': employee.id,
                            'year':self.year,
                            'employee_contract':employee.contract_id.id

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



