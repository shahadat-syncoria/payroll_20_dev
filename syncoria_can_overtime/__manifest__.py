# -*- coding: utf-8 -*-
{
    "name": "Syncoria Canada Payroll Overtime Banked Hour",
    "version": "19.1.2",
    "summary": """
        This Module is for calculating Canada overtime Banked Hour.
    """,
    "description": """
        This Module is for calculating overtime Hour.
    """,
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Uncategorized",
    # any module necessary for this one to work correctly
    "depends": ["hr_attendance", "hr_holidays", "syncoria_can_payroll", "syncoria_payroll_timesheet"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/hr_payroll_overtime_data.xml",
        "data/salary_rules.xml",
        # "data/cron_data.xml",
        "views/hr_overtime_pay_req_view.xml",
        "views/overtime_threshold.xml",
        # "views/hr_contract.xml",
        "views/hr_attendance_overtime_store.xml",
        "views/hr_employee_view.xml",
        "views/hr_payslip.xml",
        "views/paycycle_configuration.xml",
        "wizards/manual_input_wiz.xml",
    ],
}
