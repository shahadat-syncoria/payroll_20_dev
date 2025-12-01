from odoo import fields,models,api,_
from datetime import datetime



class InheritedResUser(models.Model):
    _inherit = 'res.users'


    # ========================================== YTD Information ===================================

    ytd_cpp = fields.Float("Year To Date CPP", compute='_compute_ytd_info',related_sudo=False)
    # ytd_cpp = fields.Float("Year To Date CPP", related="employee_id.ytd_cpp",related_sudo=False)

    # CPP2

    ytd_cpp2 = fields.Float("Year To Date CPP2", compute='_compute_ytd_info',related_sudo=False)
    # ytd_cpp2 = fields.Float("Year To Date CPP2", related="employee_id.ytd_cpp2",related_sudo=False)
    # EI

    ytd_ei = fields.Float("Year To Date EI", compute='_compute_ytd_info',related_sudo=False)
    # ytd_ei = fields.Float("Year To Date EI", related="employee_id.ytd_ei",related_sudo=False)

    # EI Employer
    ytd_ei_employer = fields.Float("Year To Date Employer EI", compute='_compute_ytd_info',related_sudo=False)
    # ytd_ei_employer = fields.Float("Year To Date Employer EI", related="employee_id.ytd_ei_employer",related_sudo=False)

    # ytd_pi = fields.Float("Year To Date PI/IE", related="employee_id.ytd_pi",related_sudo=False)
    ytd_pi = fields.Float("Year To Date PI/IE", compute='_compute_ytd_info',related_sudo=False)
    ytd_irre_fed_tax = fields.Float("Year To Date Irregular Payment Fed Tax",related="employee_id.ytd_irre_fed_tax",related_sudo=False)

    # YTDIrregularPaymentProvTax
    ytd_irre_prov_tax = fields.Float("Year To Date Irregular Payment Prov Tax", related="employee_id.ytd_irre_prov_tax")

    @api.depends('employee_id.payroll_line_ids')
    def _compute_ytd_info(self):
        current_year = datetime.now().year
        for record in self:
            line_obj = record.employee_id.payroll_line_ids.filtered(lambda x: x.year == current_year)
            if line_obj:
                record.ytd_cpp = line_obj.ytd_cpp
                record.ytd_cpp2 = line_obj.ytd_cpp2
                record.ytd_ei = line_obj.ytd_ei
                record.ytd_ei_employer = line_obj.ytd_ei_employer
                record.ytd_pi = line_obj.ytd_pi
            else:
                record.ytd_cpp = 0
                record.ytd_cpp2 = 0
                record.ytd_ei = 0
                record.ytd_ei_employer = 0
                record.ytd_pi = 0


    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['ytd_cpp','ytd_cpp2','ytd_ei','ytd_ei_employer','ytd_pi','ytd_irre_fed_tax','ytd_irre_prov_tax']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['ytd_cpp','ytd_cpp2','ytd_ei','ytd_ei_employer','ytd_pi','ytd_irre_fed_tax','ytd_irre_prov_tax']




