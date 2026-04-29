# -*- coding: utf-8 -*-
{
    "name": "Syncoria Irregular Payment",
    "version": "19.0.0.2",
    "summary": """
        This is part of Syncoria Canada Payroll app which will attach Irregular pay feature""",
    "description": """
        This is part of Syncoria Canada Payroll app which will attach Irregular pay feature
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
    "installable": True,
    "application": True,
    # any module necessary for this one to work correctly
    "depends": ["base", "syncoria_can_payroll", "hr_payroll"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/salary_rules.xml",
        "views/irregular_payment_view.xml",
    ],
    # only loaded in demonstration mode
    "demo": [],
}
