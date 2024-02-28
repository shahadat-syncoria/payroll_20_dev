# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaPayrollHelper(http.Controller):
#     @http.route('/syncoria_payroll_helper/syncoria_payroll_helper', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_payroll_helper/syncoria_payroll_helper/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_payroll_helper.listing', {
#             'root': '/syncoria_payroll_helper/syncoria_payroll_helper',
#             'objects': http.request.env['syncoria_payroll_helper.syncoria_payroll_helper'].search([]),
#         })

#     @http.route('/syncoria_payroll_helper/syncoria_payroll_helper/objects/<model("syncoria_payroll_helper.syncoria_payroll_helper"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_payroll_helper.object', {
#             'object': obj
#         })
