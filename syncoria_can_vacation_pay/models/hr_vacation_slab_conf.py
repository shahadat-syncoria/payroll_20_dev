from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrVacationSlab(models.Model):
    _name = 'hr.vacation.slab'
    _description = "Vacation slab"

    start_year = fields.Integer(
        required=True
    )
    end_year = fields.Integer(
    )

    allocated_leave = fields.Integer(
        required=True
    )
    leave_percentage = fields.Float(required=True)

    _sql_constraints = [
        ('start_year', 'unique(start_year)', "Slab already exist!"),
        ('end_year', 'unique(end_year)', "Slab already exist!"),
    ]


    def _compute_display_name(self):
        for record in self:
            record.display_name = '(' + str(record.start_year)+ '-' + str(record.end_year) + ')'

    @api.constrains('start_year', 'end_year')
    def _check_date_range_overlap(self):
        for rec in self:
            overlapping_slabs = self.search([
                ('id', '!=', rec.id),
                ('start_year', '<=', rec.end_year),
                ('end_year', '>=', rec.start_year),
            ])
            if overlapping_slabs:
                raise ValidationError("Date range overlaps with an existing slab!")
