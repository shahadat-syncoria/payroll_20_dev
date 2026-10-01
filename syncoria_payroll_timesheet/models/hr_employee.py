# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class Employee(models.Model):
    _inherit = 'hr.employee'

    is_timesheet_based = fields.Boolean(related='version_id.is_timesheet_based', inherited=True, readonly=False, groups="hr.group_hr_user")

    def _get_timesheets_and_working_hours_query(self, employee_ids, from_date, to_date):
        super()._get_timesheets_and_working_hours_query(employee_ids, from_date, to_date)
        return SQL("""
                    SELECT aal.employee_id as employee_id, COALESCE(SUM(aal.unit_amount), 0) as worked_hours
                    FROM account_analytic_line aal
                    WHERE aal.employee_id IN %s AND date >= %s AND date <= %s AND project_id IS NOT NULL
                    GROUP BY aal.employee_id
                """, tuple(employee_ids), from_date, to_date)
