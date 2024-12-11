# -*- coding: utf-8 -*-
import os

import werkzeug

from odoo import http
from odoo.http import request
import urllib.parse

from odoo.addons.syncoria_can_payroll.controllers.controllers  import T4WizardController


class ROEWizardController(T4WizardController):

    @http.route('/download/roe', type='http', auth='public')
    def download_roe_xml(self, model, field, id, filename=None, content_type=None, **kwargs):
        if model == 'record.of.employee' and field == 'xml_content' and id:
                record = request.env[model].sudo().browse(int(id))
                xml_content = record.xml_content
                if xml_content:
                    headers = [
                        ('Content-Type', content_type),
                        ('Content-Disposition', self.content_disposition(filename)),
                    ]
                    return request.make_response(xml_content, headers)
        return request.not_found()