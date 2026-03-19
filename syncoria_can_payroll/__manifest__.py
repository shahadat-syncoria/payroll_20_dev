# -*- coding: utf-8 -*-
{
    "name": "Syncoria Canada Payroll(Ontario)",
    "version": "19.0.0.1",
    "summary": """
        Module for Canada Payroll
       """,
    "description": """
        Module for Canada Payroll
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
    "category": "Human Resources/Payroll",
    "installable": True,
    "application": True,
    # any module necessary for this one to work correctly
    # "depends": ["base", "hr_payroll", "hr_work_entry", "hr_payroll_account", "portal", "queue_job_cron_jobrunner"],
    "depends": ["base", "hr_payroll", "hr_work_entry", "hr_payroll_account", "portal"],
    # "external_dependencies": {"python": ["requests"]},
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        # DATA
        # "data/paycycle_data.xml",
        "data/salary_category.xml",
        "data/salary_rules/salary_rules.xml",
        "data/salary_rules/cpp.xml",
        "data/salary_rules/cpp2.xml",
        "data/salary_rules/ei.xml",
        "data/salary_rules/tax.xml",
        "data/salary_rules/rrsp.xml",
        "data/emails/reminder_email.xml",
        "data/emails/batch_xml_send_email.xml",
        "data/emails/payslip_mail_template_data.xml",
        # Wizard
        "wizards/manual_input_generate_payslip.xml",
        "wizards/t4_xml_wiz.xml",
        "wizards/payslip_email_wiz.xml",
        "wizards/batch_create_draft_entry.xml",
        # Notification
        "views/notification/payroll_reminder_conf.xml",
        "views/notification/reminder_mail_schedule_action.xml",
        "views/paycycle_configuration.xml",
        # "views/res_company.xml",
        "views/tax_slab_configuration_view.xml",
        "views/fed_tax_view.xml",
        "views/prov_tax_view.xml",
        "views/hr_payroll.view.xml",
        "views/report_actions.xml",
        "views/views.xml",
        "views/hr_employee.xml",
        "views/res_partner.xml",
        # "views/hr_contract.xml",
        "views/hr_payslip.xml",
        "views/hr_payslip_run.xml",
        "views/hr_work_entry_type_view.xml",
        "views/res_company_views.xml",
        # "views/res_users.xml",
        "views/hr_salary_rule.xml",
        "views/payroll_portal_templates.xml",
        "views/hr_payslip_ytd_opening.xml",
        # "views/templates.xml",
        # ======== Report Wizards =============
        "wizards/roe_earning_per_employee_wizard_views.xml",
        "wizards/remittance_summary_wizard_views.xml",
        "wizards/receiver_general_wizard_views.xml",
        "wizards/t4_wizard_view.xml",
        # "wizards/hr_payroll_payslip_by_employee_views.xml",
        "wizards/employee_net_pay_wizard_views.xml",
        "wizards/payroll_earning_wizard_views.xml",
        "wizards/payroll_update_wizard_views.xml",
        "wizards/paycycle_config_update_wizard.xml",
        "wizards/ytd_payroll_earning_wizard_views.xml",
        "wizards/report_wizards/eht_report_wizard.xml",
        # ======== Reports =============
        "reports/roe_earning_per_employee_report_view.xml",
        "reports/remittance_summary_report_view.xml",
        "reports/rgr_report_view.xml",
        "reports/employee_net_pay_report.xml",
        "reports/payroll_earning_report.xml",
        "reports/eht_pdf_report.xml",
        "reports/ytd_payroll_earning_report.xml",
        # ======== Menus ===============
        "views/menus.xml",
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "syncoria_can_payroll/static/src/css/table.css",
        ],
        "web.assets_backend": [
            "syncoria_can_payroll/static/src/**/*",
        ],
    },
}
