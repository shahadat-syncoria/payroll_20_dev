# -*- coding: utf-8 -*-
{
    "name": "Payroll based on timesheet",
    "version": "19.0.0.1",
    "summary": """
            This module is for generate payslip based on timesheet.
        """,
    "description": """
        This module is for generate payslip based on timesheet.
    """,
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    "category": "Human Resources/Payroll",
    # any module necessary for this one to work correctly
    "depends": [
        "timesheet_grid",
        "syncoria_can_payroll",
        "hr_work_entry",
        "hr_payroll",
    ],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/hr_payslip.xml",
        # 'views/views.xml',
        # 'views/templates.xml',
        # 'views/hr_contract_inherited_view.xml'
    ],
    "installable": True,
    "application": True,
}
