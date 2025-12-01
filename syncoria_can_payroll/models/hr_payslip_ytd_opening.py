from odoo import models, fields,api
from datetime import datetime
from ..helper.helper_functions import year_selection

class HrPayslipYTDOpening(models.Model):
    _name = 'hr.payslip.ytd.opening'
    _description = 'Payroll YTD Opening Balances'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    contract_domain_ids = fields.Many2many('hr.version', compute='_compute_contract_domain_ids')
    version_id = fields.Many2one(
        'hr.version', string='Contract',
        domain="[('id', 'in', contract_domain_ids)]",
        compute='_compute_version_id', store=True, readonly=False)
    struct_id = fields.Many2one('hr.payroll.structure', string="Structure",compute='_compute_struct_id')
    year = fields.Selection(
        year_selection,
        string="Year",
        default=lambda self: str(datetime.now().year)
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )
    ytd_opening_lines = fields.One2many(
        "hr.payslip.ytd.opening.line",
        'employee_opening_ytd_id'
    )

    _sql_constraints = [
        ('employee_id_year_uni', 'unique(employee_id, year)',
         'An opening balance for this salary rule already exists for this employee/year.')
    ]



    @api.depends('version_id')
    def _compute_struct_id(self):
        for slip in self.filtered(lambda p: not p.struct_id):
            slip.struct_id = slip.version_id.structure_type_id.default_struct_id \
                             or slip.employee_id.version_id.structure_type_id.default_struct_id

    @api.depends('employee_id', 'contract_domain_ids')
    def _compute_version_id(self):
        for slip in self:
            if slip.version_id and slip.employee_id == slip.version_id.employee_id:
                continue
            slip.version_id = False
            if not slip.employee_id or not slip.contract_domain_ids:
                continue
            # Add a default contract if not already defined or invalid
            contracts = slip.contract_domain_ids.filtered(lambda c: c.state == 'open')
            if not contracts:
                continue
            slip.version_id = contracts[0]._origin

    @api.depends('company_id', 'employee_id')
    def _compute_contract_domain_ids(self):
        for payslip in self:
            payslip.contract_domain_ids = self.env['hr.version'].search([
                ('company_id', '=', payslip.company_id.id),
                ('employee_id', '=', payslip.employee_id.id),
                ('state', 'in', ['open', 'close']),
            ])

    @api.onchange('employee_id','struct_id')
    def _onchange_struct_id(self):
        """When structure changes, load its salary rules into the opening lines."""
        if not self.struct_id:
            return

        # Get all salary rules linked to this structure
        rules = self.struct_id.rule_ids
        line_values = []
        existing_rule_ids = {line.salary_rule_id.id for line in self.ytd_opening_lines}

        for rule in rules:
            if rule.id not in existing_rule_ids:
                line_values.append((0, 0, {
                    'salary_rule_id': rule.id,
                    'opening_amount': 0.0
                }))

        # Append the new rules without removing existing amounts
        self.ytd_opening_lines = line_values



class HrPayslipYTDOpeningLine(models.Model):
    _name = 'hr.payslip.ytd.opening.line'
    _description = 'Payroll YTD Opening Balances Line'

    employee_opening_ytd_id = fields.Many2one(
        'hr.payslip.ytd.opening',
        string="YTD Opening",
        required=True,
        ondelete='cascade'
    )
    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string="Salary Rule",
        required=True
    )
    opening_amount = fields.Float(
        string="Opening Amount",
        default=0.0,
        required=True
    )

    _sql_constraints = [
        ('unique_line', 'unique(employee_opening_ytd_id, salary_rule_id)',
         'An opening balance for this salary rule already exists for this employee/year.')
    ]
