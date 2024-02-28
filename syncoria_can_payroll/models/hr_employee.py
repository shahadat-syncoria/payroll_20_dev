from odoo import models, api, fields, _


class InhertitedHrEmployee(models.Model):
    _inherit = 'hr.employee'

    _sql_constraints = [
        ('identification_id_len', 'CHECK (LENGTH(identification_id) = 9)', ('Social Insurance Number Must be of 9 digits.')),
        # ('registration_number_verification', 'CHECK (registration_number SIMILAR TO ^[178][0-9]{8}(RP|RW)[0-9]{4}$)', ('Payroll Account Number Must Match patterns.')),
    ]

    employee_prpp_dpsp_rgst_nbr = fields.Integer(string="RPP or DPSP Registration Number Registration Number", groups='hr.group_hr_user',required=True)
    sync_first_contract_date = fields.Date("First Contract Date", compute='compute_first_contract_date', store=True, groups='hr.group_hr_user')
    registration_number = fields.Char('Registration Number of the Employee', groups="hr.group_hr_user", required=True, help="-Must be 15 alphanumeric characters \
                                                                                                                        -The first character must be either '1', '7' or '8' \
                                                                                                                        -The first 9 characters must be numeric and not all zeros \
                                                                                                                        -The 10th and 11th characters must be 'RP' (or 'RW' for Demo).\
                                                                                                                        -The last four characters must be numeric and greater than '0000'.")
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True, required=True)
    @api.depends('first_contract_date')
    def compute_first_contract_date(self):
        for rec in self:
            if rec.first_contract_date:
                rec.sync_first_contract_date = rec.first_contract_date
