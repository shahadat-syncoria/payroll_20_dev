# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaCanVacationPay(http.Controller):
#     @http.route('/syncoria_can_vacation_pay/syncoria_can_vacation_pay', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_can_vacation_pay/syncoria_can_vacation_pay/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_can_vacation_pay.listing', {
#             'root': '/syncoria_can_vacation_pay/syncoria_can_vacation_pay',
#             'objects': http.request.env['syncoria_can_vacation_pay.syncoria_can_vacation_pay'].search([]),
#         })

#     @http.route('/syncoria_can_vacation_pay/syncoria_can_vacation_pay/objects/<model("syncoria_can_vacation_pay.syncoria_can_vacation_pay"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_can_vacation_pay.object', {
#             'object': obj
#         })
