# -*- coding: utf-8 -*-
{
    'name': "Payroll based on timesheet",

    'summary': """
            This module is for generate payslip based on timesheet.
        """,

    'description': """
        This module is for generate payslip based on timesheet.
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    'category': 'Human Resources/Payroll',
    'version': '17.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['timesheet_grid','syncoria_can_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
        # 'views/hr_contract_inherited_view.xml'
    ],

    'license': 'LGPL-3',
    'installable': True,
    'application': True,

}
