from odoo import fields,api,models,_

class ResCompanyPayroll(models.Model):
    _inherit = 'res.company'

    paygroup = fields.Many2one('paycycle.config')

    payroll_account_number = fields.Char('Payroll Account Number', groups="hr.group_hr_user", help="-Must be 15 alphanumeric characters \
                                                                                                                            -The first character must be either '1', '7' or '8' \
                                                                                                                            -The first 9 characters must be numeric and not all zeros \
                                                                                                                            -The 10th and 11th characters must be 'RP' (or 'RW' for Demo).\
                                                                                                                            -The last four characters must be numeric and greater than '0000'.")
    employer_payroll_ref = fields.Char(string="Employer's Payroll Reference Number")