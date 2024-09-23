from odoo import fields,models,api,_
from odoo.exceptions import UserError



class InheritedResUser(models.Model):
    _inherit = ['res.users']


    # ========================================== YTD Information ===================================

    ytd_cpp = fields.Float("Year To Date CPP", related="employee_id.ytd_cpp",related_sudo=False)

    # CPP2

    ytd_cpp2 = fields.Float("Year To Date CPP2", related="employee_id.ytd_cpp2",related_sudo=False)
    # EI

    ytd_ei = fields.Float("Year To Date EI", related="employee_id.ytd_ei",related_sudo=False)

    # EI Employer

    ytd_ei_employer = fields.Float("Year To Date Employer EI", related="employee_id.ytd_ei_employer",related_sudo=False)

    ytd_pi = fields.Float("Year To Date PI/IE", related="employee_id.ytd_pi",related_sudo=False)
    ytd_irre_fed_tax = fields.Float("Year To Date Irregular Payment Fed Tax",related="employee_id.ytd_irre_fed_tax",related_sudo=False)


    # YTDIrregularPaymentProvTax
    ytd_irre_prov_tax = fields.Float("Year To Date Irregular Payment Prov Tax", related="employee_id.ytd_irre_prov_tax")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['ytd_cpp','ytd_cpp2','ytd_ei','ytd_ei_employer','ytd_pi','ytd_irre_fed_tax','ytd_irre_prov_tax']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['ytd_cpp','ytd_cpp2','ytd_ei','ytd_ei_employer','ytd_pi','ytd_irre_fed_tax','ytd_irre_prov_tax']




