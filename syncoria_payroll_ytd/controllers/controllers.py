# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaPayrollYtd(http.Controller):
#     @http.route('/syncoria_payroll_ytd/syncoria_payroll_ytd', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_payroll_ytd/syncoria_payroll_ytd/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_payroll_ytd.listing', {
#             'root': '/syncoria_payroll_ytd/syncoria_payroll_ytd',
#             'objects': http.request.env['syncoria_payroll_ytd.syncoria_payroll_ytd'].search([]),
#         })

#     @http.route('/syncoria_payroll_ytd/syncoria_payroll_ytd/objects/<model("syncoria_payroll_ytd.syncoria_payroll_ytd"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_payroll_ytd.object', {
#             'object': obj
#         })

