from odoo import fields,models,api,_
from odoo.exceptions import UserError


class InheritedResPartner(models.Model):
    _inherit = 'res.partner'

    company_name1 = fields.Char(string="Employer Name - Line 1",size=30)
    company_name2 = fields.Char(string="Employer Name - Line 2",size=30)
    company_name3 = fields.Char(string="Employer Name - Line 3",size=30)
    company_name3 = fields.Char(string="Employer Name - Line 3",size=30)
    employeer_contact_id = fields.Many2one('res.partner',string='Employer Contact Person',)
    employeer_pprtr_1_sin = fields.Integer(string="Proprietor #1 Social Insurance Number (SIN)",)
    employeer_pprtr_2_sin = fields.Integer(string="Proprietor #2 Social Insurance Number (SIN)",)
    employeer_cra_number = fields.Char(string="Employer CRA Number",default="")


class InheritedResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    acc_number = fields.Char('Account Number', required=True)




