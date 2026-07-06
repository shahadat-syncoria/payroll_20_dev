from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyncoriaHrWorkEntryType(models.Model):
    _inherit = "hr.salary.rule"

    T4_DEFAULT_FIELD_BY_FLAG = {
        "is_insurable_earning": "employee_ei_insu_ern_amt",
        "is_pensionable": "canada_cpp_qpp_ern_amt",
    }

    is_insurable_earning = fields.Boolean("Calculate as Insurable Earning",default=False,
                                          help="This rule in payslip will be calculated as Insurable Earning, if this field is true. ")
    is_pensionable = fields.Boolean("Calculate as Pensionable",default=False,
                                    help="This rule in payslip will be calculated in CPP and CPP2, if this field is true. ")
    is_vacation_pay = fields.Boolean("Accrued Vacation Pay",default=False,
                                     help="This rule in payslip will be calculated for storing the vacation pay, if this field is true. ")
    is_irregular_payment = fields.Boolean("Calculate as Irregular Payment",default=False)
    cat_code = fields.Char(related="category_id.code", string="Category Code")
    is_rrsp = fields.Boolean("Calculate as RRSP",default=False)
    is_wsib = fields.Boolean("Calculate as WSIB", default=False)
    is_eht = fields.Boolean("Calculate as EHT", default=False)

    selected_t4_statement_fields = fields.Many2many(
        'syncoria_can_payroll.t4_box_selection',
        'statement_remuneration_t4_statement_field_rel',
        'remuneration_id',
        'statement_field_id',
        string='Select T4 Statement Fields',
        domain=[('active', '=', True)],
        help='Select T4 statement remuneration fields that will be used for this salary rule.',
    )

    def _get_managed_t4_statement_fields(self):
        return self.env["syncoria_can_payroll.t4_box_selection"].with_context(active_test=False).search([
            ("field_name", "in", list(self.T4_DEFAULT_FIELD_BY_FLAG.values()))
        ])

    def _get_default_t4_statement_fields(self):
        enabled_field_names = [
            field_name
            for flag_name, field_name in self.T4_DEFAULT_FIELD_BY_FLAG.items()
            if self[flag_name]
        ]
        if not enabled_field_names:
            return self.env["syncoria_can_payroll.t4_box_selection"]
        return self.env["syncoria_can_payroll.t4_box_selection"].search([
            ("field_name", "in", enabled_field_names),
            ("active", "=", True),
        ])

    def _sync_default_t4_statement_fields(self):
        managed_fields = self._get_managed_t4_statement_fields()
        for rule in self:
            target_fields = (rule.selected_t4_statement_fields - managed_fields) | rule._get_default_t4_statement_fields()
            if set(target_fields.ids) != set(rule.selected_t4_statement_fields.ids):
                rule.with_context(skip_t4_default_sync=True).write({
                    "selected_t4_statement_fields": [(6, 0, target_fields.ids)],
                })

    def _should_sync_default_t4_statement_fields(self, vals):
        return (
            "selected_t4_statement_fields" in vals
            or bool(set(self.T4_DEFAULT_FIELD_BY_FLAG) & set(vals))
        )

    @api.onchange("is_insurable_earning", "is_pensionable")
    def _onchange_selected_t4_statement_fields(self):
        managed_fields = self._get_managed_t4_statement_fields()
        for rule in self:
            rule.selected_t4_statement_fields = (
                (rule.selected_t4_statement_fields - managed_fields) | rule._get_default_t4_statement_fields()
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if record._should_sync_default_t4_statement_fields(vals):
                record._sync_default_t4_statement_fields()
        return records

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("skip_t4_default_sync"):
            return result
        if self._should_sync_default_t4_statement_fields(vals):
            self._sync_default_t4_statement_fields()
        return result
