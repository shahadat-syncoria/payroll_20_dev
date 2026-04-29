from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields,api,models,_

class ResCompanyPayroll(models.Model):
    _inherit = 'res.company'


    ytd_reset_day = fields.Integer(
        default=1,
        string='YTD Reset Day of the month',
        help="""Day where the YTD will be reset every year. If zero or negative, then the first day of the month will be selected instead.
         If greater than the last day of a month, then the last day of the month will be selected instead.""")
    ytd_reset_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')],
        default='1', string='YTD Reset Month')


    def get_last_ytd_reset_date(self, target_date):
        self.ensure_one()
        last_ytd_reset_date = date(target_date.year, int(self.ytd_reset_month), self.ytd_reset_day)
        if last_ytd_reset_date > target_date:
            last_ytd_reset_date += relativedelta(years=-1)
        return last_ytd_reset_date
