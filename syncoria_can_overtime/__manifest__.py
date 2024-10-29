# -*- coding: utf-8 -*-
{
    'name': "Syncoria Canada Payroll Overtime Banked Hour",

    'summary': """
        This Module is for calculating Canada overtime Banked Hour.
    """,

    'description': """
        This Module is for calculating overtime Hour.
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '17.3',

    # any module necessary for this one to work correctly
    'depends': ['syncoria_can_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/hr_payroll_overtime_data.xml',
        'data/hr_payroll_overtime_data.xml',
        'data/salary_rules.xml',
        'data/cron_data.xml',
        'views/hr_overtime_pay_req_view.xml',
        'views/hr_contract.xml',
        'views/hr_attendance_overtime_store.xml',
        'views/hr_employee_view.xml',
        'views/hr_payslip.xml',



    ],
'license': 'LGPL-3',
}
