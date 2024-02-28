###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    batch_id = fields.Char("Batch ID", readonly=True)
    bambora_batch_payment_id = fields.Many2one("batch.payment.tracking", "Bambora Batch Payment", readonly=True)
    bambora_batch_state = fields.Selection(string="Bambora State", related="bambora_batch_payment_id.state")
    bambora_batch_status = fields.Char("Bambora Status", related="bambora_batch_payment_id.status")
