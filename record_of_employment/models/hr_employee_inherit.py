from odoo import api, fields, models



class HrEmployeeInherit(models.Model):
    _inherit = "hr.employee"


    payroll_ref = fields.Char(string="Employer's Payroll Account Number",groups= 'hr.group_hr_user')