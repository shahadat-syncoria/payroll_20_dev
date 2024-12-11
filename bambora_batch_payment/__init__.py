###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo.addons.payment import reset_payment_provider

from odoo import _
from odoo.service import common
from . import controllers
from . import models
from . import tests
from odoo.addons.payment import setup_provider, reset_payment_provider


def pre_init_check(cr):
    version_info = common.exp_version()
    server_serie = version_info.get("server_serie")
    if server_serie != "18.0":
        raise Warning(_('Module support Odoo series 18.0 found {}.').format(server_serie))
    return True


def uninstall_hook(env):
    reset_payment_provider(env,"bamboraeft")
