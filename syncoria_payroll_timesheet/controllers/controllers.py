# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaPayrollTimesheet(http.Controller):
#     @http.route('/syncoria_payroll_timesheet/syncoria_payroll_timesheet', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_payroll_timesheet/syncoria_payroll_timesheet/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_payroll_timesheet.listing', {
#             'root': '/syncoria_payroll_timesheet/syncoria_payroll_timesheet',
#             'objects': http.request.env['syncoria_payroll_timesheet.syncoria_payroll_timesheet'].search([]),
#         })

#     @http.route('/syncoria_payroll_timesheet/syncoria_payroll_timesheet/objects/<model("syncoria_payroll_timesheet.syncoria_payroll_timesheet"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_payroll_timesheet.object', {
#             'object': obj
#         })
