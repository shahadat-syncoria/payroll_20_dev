# -*- coding: utf-8 -*-
{
    'name': "Syncoria Canada Vacation Pay",

    'summary': """
        This is part of Syncoria Canada Payroll app which will attach vacation pay feature""",

    'description': """
       This is part of Syncoria Canada Payroll which will attach vacation pay feature
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    'category': 'Human Resources/Payroll',
    'version': '17.0.0.14',
    'installable': True,
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'syncoria_can_payroll', 'hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/hr_vacation_pay_security.xml',
        'data/cron_data.xml',
        # Data
        'data/ir_sequence.xml',

        'data/salary_category.xml',
        'data/salary_rules.xml',
        # Views
        'views/vacation_pay_conf.xml',
        'views/hr_leave_type_view.xml',
        'views/hr_vacation_pay_view.xml',
        'views/hr_employee.xml',
        'views/vacation_pay_slab.xml',
        'views/res_users.xml',
        'views/hr_work_entry_type.xml',
        'views/hr_payslip.xml',
        # Report
        'report/payslip.xml',
        'report/vacation_slab_for_existing_employees.xml',

        'wizards/vacation_slab_update.xml'
    ],
    'license': 'LGPL-3',
}
