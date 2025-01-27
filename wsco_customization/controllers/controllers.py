# -*- coding: utf-8 -*-
# from odoo import http


# class WscoCustomization(http.Controller):
#     @http.route('/wsco_customization/wsco_customization', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wsco_customization/wsco_customization/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wsco_customization.listing', {
#             'root': '/wsco_customization/wsco_customization',
#             'objects': http.request.env['wsco_customization.wsco_customization'].search([]),
#         })

#     @http.route('/wsco_customization/wsco_customization/objects/<model("wsco_customization.wsco_customization"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wsco_customization.object', {
#             'object': obj
#         })

