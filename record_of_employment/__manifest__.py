# -*- coding: utf-8 -*-
{
    "name": "Record Of Employment (ROE)",
    "version": "20.0.0.7",
    "summary": """
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

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'syncoria_can_payroll','syncoria_can_vacation_pay'],

    # always loaded
    'data': [
        'data/batch_xml_send_roe.xml',
        'data/hr_work_entry_data.xml',
        'views/record_of_employee.xml',
        'views/hr_employee_view.xml',
        'views/hr_payslip.xml',
        'views/hr_contract_history.xml',
        'views/menu.xml',
        'wizard/roe_paycycle_excel_wizard_view.xml',
        'security/ir.access.csv',
    ],
    'license': 'LGPL-3',

}
