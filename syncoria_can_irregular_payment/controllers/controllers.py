# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaCanIrregularPayment(http.Controller):
#     @http.route('/syncoria_can_irregular_payment/syncoria_can_irregular_payment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_can_irregular_payment/syncoria_can_irregular_payment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_can_irregular_payment.listing', {
#             'root': '/syncoria_can_irregular_payment/syncoria_can_irregular_payment',
#             'objects': http.request.env['syncoria_can_irregular_payment.syncoria_can_irregular_payment'].search([]),
#         })

#     @http.route('/syncoria_can_irregular_payment/syncoria_can_irregular_payment/objects/<model("syncoria_can_irregular_payment.syncoria_can_irregular_payment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_can_irregular_payment.object', {
#             'object': obj
#         })
