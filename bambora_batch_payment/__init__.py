###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo.addons.payment import reset_payment_provider

from odoo import _
from odoo.exceptions import Warning
from odoo.service import common
from . import controllers
from . import models
from . import tests


def pre_init_check(cr):
    version_info = common.exp_version()
    server_serie = version_info.get("server_serie")
    if server_serie != "16.0":
        raise Warning(_('Module support Odoo series 16.0 found {}.').format(server_serie))
    return True


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, "bamboraeft")
