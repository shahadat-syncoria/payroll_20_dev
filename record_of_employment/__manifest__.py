# -*- coding: utf-8 -*-
{
    'name': "Record Of Employment (ROE)",

    'summary': """
    This module will help to record ROE data.
    """,

    'description': """
        This module will help to record ROE data.
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Payroll',
    'version': '17.0.0.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'syncoria_can_payroll','syncoria_can_vacation_pay'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/batch_xml_send_roe.xml',
        'views/record_of_employee.xml',
        # 'views/hr_employee_view.xml',
        'views/hr_payslip.xml',
        'views/hr_contract_history.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',

}
