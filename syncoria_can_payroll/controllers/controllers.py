# -*- coding: utf-8 -*-
import os

import werkzeug

from odoo import http
from odoo.http import request
import urllib.parse


class T4WizardController(http.Controller):

    def content_disposition(self, filename):
        quoted_filename = urllib.parse.quote(filename)
        return 'attachment; filename="%s"; filename*=UTF-8\'\'%s' % (quoted_filename, quoted_filename)

    @http.route('/download/remuneration', type='http', auth='public')
    def download_t4_xml(self, model, field, id, filename=None, content_type=None, **kwargs):
        if model == 'statement.remuneration' and field == 'xml_content' and id:
            record = request.env[model].sudo().browse(int(id))
            xml_content = record.xml_content
            if xml_content:
                headers = [
                    ('Content-Type', content_type),
                    ('Content-Disposition', self.content_disposition(filename)),
                ]
                return request.make_response(xml_content, headers)
        if model == 'statement.remuneration.wizard' and field == 'pdf_content' and id:
            record = request.env[model].sudo().browse(int(id))
            # xml_content = record.file_c
            # if xml_content:
            #     headers = [
            #         ('Content-Type', content_type),
            #         ('Content-Disposition', self.content_disposition(filename)),
            #     ]
            #     return request.make_response(xml_content, headers)
            return werkzeug.wrappers.Response(
                record.xml_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
        return request.not_found()

    @http.route('/download/pdf', type='http', auth='public')
    def download_pdf(self, file_path, file_name, **kwargs):
        # Retrieve the model record
        # model = request.env['statement.remuneration.wizard'].sudo().browse(int(id))

        # file_path = '/path/to/your/pdf/file.pdf'
        import ast
        from odoo.tools import pdf
        files_list = []
        for file_path in ast.literal_eval(kwargs.get('file_paths')):
            if not os.path.isfile(file_path[0]):
                return http.request.not_found()

            with open(file_path[0], 'rb') as file:
                file_content = file.read()

            # Retrieve the PDF file from the model's binary field
            file_content = file_content

            if not file_content:
                return http.request.not_found()
            files_list.append(file_content)

        merged_pdf = pdf.merge_pdf(files_list)

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', f'attachment; filename={file_name}')
        ]

        os.remove(file_path[0])

        return request.make_response(merged_pdf, headers=pdfhttpheaders)




        #
        # # Serve the file for download
        # response = request.make_response(
        #     file_content,
        #     headers=[
        #         ('Content-Type', 'application/pdf'),
        #         ('Content-Disposition', f'attachment; filename={file_name}')
        #     ]
        # )
        # os.remove(file_path)

        # return response

    @http.route('/t4/download_xml', type='http', auth='user')
    def download_t4_batch_xml(self, field, id, filename=None, content_type='application/xml', **kwargs):
        if field == 'xml_content' and id:
            record = request.env['statement.remuneration'].sudo().browse(int(id))
            xml_content = record.xml_content
            if xml_content:
                headers = [
                    ('Content-Type', content_type),
                    ('Content-Disposition', self.content_disposition(filename)),
                ]
                return request.make_response(xml_content, headers)
        return request.not_found()

# class SyncoriaCanPayroll(http.Controller):
#     @http.route('/syncoria_can_payroll/syncoria_can_payroll', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/syncoria_can_payroll/syncoria_can_payroll/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('syncoria_can_payroll.listing', {
#             'root': '/syncoria_can_payroll/syncoria_can_payroll',
#             'objects': http.request.env['syncoria_can_payroll.syncoria_can_payroll'].search([]),
#         })

#     @http.route('/syncoria_can_payroll/syncoria_can_payroll/objects/<model("syncoria_can_payroll.syncoria_can_payroll"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('syncoria_can_payroll.object', {
#             'object': obj
#         })
