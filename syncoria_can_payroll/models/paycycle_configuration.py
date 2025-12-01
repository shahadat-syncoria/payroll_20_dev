from datetime import datetime,timedelta
from calendar import monthrange
from odoo.exceptions import UserError
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from ..helper.helper_functions import year_selection



def generate_date_ranges(start_date, pay_cycle):
    date_ranges = []
    current_date = start_date

    if pay_cycle == "12":
        for _ in range(12):
            _, last_day = monthrange(current_date.year, current_date.month)
            end_date = current_date.replace(day=last_day)
            date_ranges.append((0, 0, {
                'name':current_date.strftime('%B')+'('+pay_cycle+')',
                'start_date':current_date,
                'end_date':end_date,
            }))
            current_date = end_date + timedelta(days=1)
    elif pay_cycle == "24":
        month_counts = {}
        for _ in range(24):
            month_name = current_date.strftime('%B')

            if month_name in month_counts:
                month_counts[month_name] += 1
                repetition_count = month_counts[month_name]
                month_name = f"{month_name} - {repetition_count}"
            else:
                month_counts[month_name] = 1
                month_name = f"{month_name} - 1"

            if current_date.day == 1:
                end_date = current_date + timedelta(days=14)
            else:
                _, last_day = monthrange(current_date.year, current_date.month)
                end_date = current_date.replace(day=last_day)

            date_ranges.append((0, 0, {
                'name': month_name+' Pay period'+'('+pay_cycle+')',
                'start_date': current_date,
                'end_date': end_date,
            }))

            current_date = end_date + timedelta(days=1)
    elif pay_cycle == "26":
        month_counts = {}
        for _ in range(26):
            month_name = current_date.strftime('%B')

            if month_name in month_counts:
                month_counts[month_name] += 1
                repetition_count = month_counts[month_name]
                month_name = f"{month_name} - {repetition_count}"
            else:
                month_counts[month_name] = 1
                month_name = f"{month_name} - 1"
            end_date = current_date + timedelta(days=13)
            # date_ranges.append((current_date, end_date))
            date_ranges.append((0, 0, {
                'name': month_name+' Pay period'+'('+pay_cycle+')',
                'start_date': current_date,
                'end_date': end_date,
            }))
            current_date = end_date + timedelta(days=1)
    elif pay_cycle == "52":
        month_counts = {}
        for _ in range(52):
            month_name = current_date.strftime('%B')

            if month_name in month_counts:
                month_counts[month_name] += 1
                repetition_count = month_counts[month_name]
                month_name = f"{month_name} - {repetition_count}"
            else:
                month_counts[month_name] = 1
                month_name = f"{month_name} - 1"

            end_date = current_date + timedelta(days=6)
            # date_ranges.append((current_date, end_date))
            date_ranges.append((0, 0, {
                'name': month_name+' Pay period'+'('+pay_cycle+')',
                'start_date': current_date,
                'end_date': end_date,
            }))
            current_date = end_date + timedelta(days=1)
    else:
        raise ValueError("Invalid pay cycle")

    return date_ranges

class PayrollPaycycle(models.Model):
    _name = 'paycycle.config'
    _description = 'Payroll Pay cycle Configuration'
    _rec_name = 'pay_cycle'

    @api.model
    def date_selection(self):
        date = 1  # replace 2000 with your a start year
        date_list = []
        while date != 31:  # replace 30 with your end year
            date_list.append((str(date), str(date)))
            date += 1
        return date_list

    paystub_group_name = fields.Char("Pay Cycle Group", required=True)
    pay_cycle = fields.Selection([
        ('52', '52'),
        ('26', '26'),
        ('24', '24'),
        ('12', '12'),
    ], default='12', string="Pay Cycle")
    start_date = fields.Selection(
        date_selection,
        string="Start Date",
    )
    # frequency = fields.Selection([
    #     ('5','5'),
    #     ('14','14'),
    #     ('15','15'),
    #     ('30','30'),
    # ])
    paycycle_period_ids = fields.One2many(
        comodel_name='paycycle.period',
        inverse_name='paycycle_config_id',
        string='Paycycle Periods',
    )
    paycycle_period_year_slab_ids = fields.One2many(
        comodel_name='paycycle.period.year.slab',
        inverse_name='paycycle_config_id',
        string='Paycycle Period Slabs',
    )

    _sql_constraints = [
        ('pay_cycle', 'unique(pay_cycle)', "A Pay cycle already exists."),
    ]

    # A pay cycle cannot be deleted if a employee is attached in that paycycle
    def unlink(self):
        for rec in self:
            is_linked_paycycle = self.env["hr.version"].search_count([('salary_pay_cycle.id','=', rec.id),('state','!=', 'cancel')],limit=1)
            if is_linked_paycycle > 0:
                raise ValidationError(_("You cannot delete a pay cycle which have a employee."))

        return super(PayrollPaycycle, self).unlink()

    @api.onchange('pay_cycle','start_date')
    def _onchange_paycycle(self):
        self.ensure_one()
        for rec in self:
            rec.paycycle_period_ids = [(6, 0, [])]



            # employee_line_list = [(0, 0, {
            #     'employee_id': employee_id.id,
            # })]
            if rec.start_date:
                start_date = datetime.strptime(f'{fields.Date.today().year}-01-{rec.start_date}', '%Y-%m-%d')
                result = generate_date_ranges(start_date,rec.pay_cycle)
                rec.paycycle_period_ids = result

    def _compute_display_name(self):
        for record in self:
            if record.paystub_group_name and record.pay_cycle:
                record.display_name = record.paystub_group_name + '(' + record.pay_cycle + ')'
            else:
                super()._compute_display_name()

    @api.model
    def action_update_batch_paycycle_config(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch Update Payslip Copnfig',
            'res_model': 'paycycle.config.update.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

class PaycyclePeriodYearSlab(models.Model):
    _name = 'paycycle.period.year.slab'
    _description = 'Pay Cycle Period Year Slab'
    _rec_name = 'year'

    paycycle_config_id = fields.Many2one('paycycle.config')
    year = fields.Selection(
        year_selection,
        string="Year"
    )
    paycycle_period_ids = fields.One2many(
        comodel_name='paycycle.period',
        inverse_name='paycycle_year_slab_id',
        string='Paycycle Periods',
    )

    @api.constrains('year')
    def _check_year(self):
        self.ensure_one()
        records_count = self.search_count([('year', '=', self.year),('paycycle_config_id', '=', self.paycycle_config_id.id)])
        if records_count > 1:
            raise UserError(_("Duplicate Error: Year already exists."))

    @api.onchange('year')
    def _onchange_year(self):
        self.ensure_one()
        for rec in self:
            rec.paycycle_period_ids = [(6, 0, [])]
            if rec.paycycle_config_id.start_date and rec.year:
                # Assume 'year' is an integer field representing the selected year
                selected_year = rec.year
                print(selected_year)
                start_date = datetime.strptime(f'{selected_year}-01-{rec.paycycle_config_id.start_date}', '%Y-%m-%d')
                print('start_date', start_date, rec.paycycle_config_id.pay_cycle)
                result = generate_date_ranges(start_date, rec.paycycle_config_id.pay_cycle)
                rec.paycycle_period_ids = result

    # A pay period cannot be deleted if there is a generated payslip for that pay period
    def unlink(self):
        for rec in self:
            is_linked_payperiod = self.env["hr.payslip"].search_count([('pay_cycle_period.id','=', rec.id),('state','!=', 'cancel')],limit=1)
            if is_linked_payperiod >0:
                raise ValidationError(_("You cannot delete a pay period which have a generated payslip."))

        return super(PaycyclePeriodYearSlab, self).unlink()


class PaycyclePeriod(models.Model):
    _name = 'paycycle.period'
    _description = 'Pay Cycle Period'
    _rec_name = 'name'

    paycycle_config_id = fields.Many2one('paycycle.config')
    paycycle_year_slab_id = fields.Many2one('paycycle.period.year.slab')
    year = fields.Selection(
        string="Year",
        related='paycycle_year_slab_id.year',store=True
    )
    name = fields.Char("Pay Period")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")


    # A pay period cannot be deleted if there is a generated payslip for that pay period
    def unlink(self):
        for rec in self:
            is_linked_payperiod = self.env["hr.payslip"].search_count([('pay_cycle_period.id','=', rec.id),('state','!=', 'cancel')],limit=1)
            if is_linked_payperiod >0:
                raise ValidationError(_("You cannot delete a pay period which have a generated payslip."))

        return super(PaycyclePeriod, self).unlink()
