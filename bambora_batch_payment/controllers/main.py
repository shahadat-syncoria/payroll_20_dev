# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BamboraEftController(http.Controller):


    @http.route('/payment/bamboraeft/get_provider_info', type='jsonrpc', auth='public')
    def bamboraeft_get_provider_info(self, provider_id):
        """ Return public information on the provider.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        return {
            'state': providersudo.state,
            'payment_method_type': providersudo.bamboraeft_tran_type,
            # # The public API key solely used to identify the seller account with Authorize.Net
            # 'login_id': providersudo.authorize_login,
            # # The public client key solely used to identify requests from the Accept.js suite
            # 'client_key': providersudo.authorize_client_key,
        }



    @http.route('/payment/bamboraeft/payment', type='jsonrpc', auth='public')
    def bambora_payment(self, reference, data, providerid):
        """ Simulate the response of a payment request.

        :param str reference: The reference of the transaction
        :param str customer_input: The payment method details
        :return: None
        """
        # Make the payment request to Adyen
        providersudo = request.env['payment.provider'].sudo().browse(providerid).exists()
        print('data', data, reference)
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])

        data['providerid'] = providerid
        data['tx_id'] = tx_sudo.id
        response_content = providersudo._bambora_make_request(
            payload=data,
        )

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'bamboraeft', dict(response_content, reference=reference, data=data),  # Match the transaction
        )
        return response_content
