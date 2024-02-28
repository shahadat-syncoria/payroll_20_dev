import base64
import logging

from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)

def _get_authorization(merchant_id, api_key):
    message = str(merchant_id + ":" + api_key).strip()
    base64_bytes = base64.b64encode(message.encode("ascii"))
    base64_message = base64_bytes.decode("ascii")
    _logger.info(base64_bytes.decode("ascii"))
    return base64_message

