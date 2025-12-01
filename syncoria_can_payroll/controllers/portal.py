# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import  http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import  request, route, content_disposition

class PayrollCustomerPortal(CustomerPortal):

    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        payslip = request.env['hr.payslip'].sudo()
        emp_id = request.env["hr.employee"].sudo().search([("portal_user_id", "=", request.env.user.id)], limit=1)
        domain = [('employee_id', '=', emp_id.id), ('state', 'in', ('done', 'paid'))]
        payslip_count = payslip.search_count(domain)
        values['payslip_count'] = payslip_count
        return request.render("portal.portal_my_home", values)

    # ------------------------------------------------------------
    # My Payroll
    # ------------------------------------------------------------

    @http.route(['/my/payslip', '/my/payslip/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_payrolls(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        payslip = request.env['hr.payslip'].sudo()
        emp_id = request.env["hr.employee"].sudo().search([("portal_user_id", "=", request.env.user.id)], limit=1)
        domain = [('employee_id', '=', emp_id.id),('state', 'in', ('done', 'paid'))]

        # payslip count
        payslip_count = payslip.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/payslip",
            url_args={'sortby': sortby},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        payslips = payslip.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'payslips': payslips,
            'page_name': 'payslip',
            'default_url': '/my/payslip',
            'pager': pager,
            'sortby': sortby
        })
        return request.render("syncoria_can_payroll.portal_my_payslips", values)

    @http.route(['/my/payslip/<int:pay_id>'], type='http', auth="public", website=True)
    def portal_my_project(self, pay_id=None, **kw):
        payslip_obj = (
            request.env["hr.payslip"]
            .sudo()
            .search([("id", "=", pay_id)])
        )
        total_amount = sum(x.amount for x in payslip_obj.line_ids)
        ctx = {
            "detailed_payslip": payslip_obj.line_ids,
            "pay_cycle_period_name": payslip_obj.pay_cycle_period.name,
            "total_amount": total_amount,
            "payslip": payslip_obj,
            'page_name': 'payslip_details'
        }
        return request.render("syncoria_can_payroll.portal_my_payslip", ctx)

    # print emp individual payslip form portal
    @http.route(['/action_print_payslip'], type="http", auth="public", csrf=False, website=True)
    def action_print_payslip(self, **kwargs):
        payslip_id = int(kwargs.get('payslip_id'))
        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'hr_payroll.action_report_payslip',
            payslip.id,
        )[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(f'Payslip_{payslip_id}.pdf')),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
