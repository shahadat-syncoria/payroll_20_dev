# -*- coding: utf-8 -*-
{
    "name": "syncoria_payroll_helper",
    "version": "19.1.1",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
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
    "depends": ["base", "syncoria_can_payroll"],
    # always loaded
    "data": [
        # "views/hr_payslip.xml",
        # "views/hr_payslip_run.xml",
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
}
