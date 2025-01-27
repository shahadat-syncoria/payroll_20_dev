# -*- coding: utf-8 -*-
{
    'name': "wsco_customization",

    'summary': "Customization For WS&CO payroll",

    'description': """
Customization For WS&CO payroll
    """,

    'author': "Syncoria Inc.",
    'website': "https://www.syncoria.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Payroll',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','syncoria_can_payroll'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',

        'report/report_payslip.xml',
        'report/remittance_summary_report_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

