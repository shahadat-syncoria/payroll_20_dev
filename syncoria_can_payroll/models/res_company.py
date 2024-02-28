from odoo import fields,api,models,_

class ResCompanyPayroll(models.Model):
    _inherit = 'res.company'

    paygroup = fields.Many2one('paycycle.config')