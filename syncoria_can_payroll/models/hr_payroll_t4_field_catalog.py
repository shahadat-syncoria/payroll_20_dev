# -*- coding: utf-8 -*-
from odoo import fields, models


class T4BoxSelection(models.Model):
    _name = 'syncoria_can_payroll.t4_box_selection'
    _description = 'T4 Box Selection Configuration'
    _order = "box_number"
    _rec_name = 'field_description'

    box_number = fields.Integer(
        string='Box Number',
        required=True,
        index=True,
    )
    field_name = fields.Char(
        string='Field Name',
        required=True,
    )
    field_description = fields.Char(
        string='Description',
        required=True,
    )
    active = fields.Boolean(
        default=True,
        index=True,
    )

    _sql_constraints = [
        ("t4_box_selection_box_number_uniq", "unique(box_number)", "Box number must be unique."),
    ]
