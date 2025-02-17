# -*- coding: utf-8 -*-
# from odoo import http


# class SyncoriaRbcDirectDeposit(http.Controller):
#     @http.route('/syncoria_rbc_direct_deposit/syncoria_rbc_direct_deposit', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_rbc_direct_deposit/syncoria_rbc_direct_deposit/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_rbc_direct_deposit.listing', {
#             'root': '/syncoria_rbc_direct_deposit/syncoria_rbc_direct_deposit',
#             'objects': http.request.env['syncoria_rbc_direct_deposit.syncoria_rbc_direct_deposit'].search([]),
#         })

#     @http.route('/syncoria_rbc_direct_deposit/syncoria_rbc_direct_deposit/objects/<model("syncoria_rbc_direct_deposit.syncoria_rbc_direct_deposit"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_rbc_direct_deposit.object', {
#             'object': obj
#         })

