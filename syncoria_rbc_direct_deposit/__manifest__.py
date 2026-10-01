# -*- coding: utf-8 -*-
{
    "name": "RBC Direct Deposit",
    "version": "20.0.2",
    "summary": "This Module is for RBC Direct Download.",
    "description": """
This Module is for RBC Direct Download
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
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Human Resources/Payroll",
    # any module necessary for this one to work correctly
    "depends": ["base", "syncoria_can_payroll"],
    # always loaded
    "data": [
        # 'security/ir.model.access.csv',
        "views/views.xml",
        "views/templates.xml",
        "views/hr_payslip_run.xml",
        "views/res_partner.xml",
        "views/res_config_settings_views.xml",
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
}
