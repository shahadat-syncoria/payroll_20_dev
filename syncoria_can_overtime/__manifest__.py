# -*- coding: utf-8 -*-
{
    'name': "Syncoria Canada Payroll Overtime",

    'summary': """
        This Module is for calculating Canada overtime.
    """,

    'description': """
        This Module is for calculating overtime.
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '17.0',

    # any module necessary for this one to work correctly
    'depends': ['syncoria_can_payroll'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/hr_payroll_overtime_data.xml',
        'data/salary_rules.xml',
        'wizards/manual_input_wiz.xml'

    ],
}
