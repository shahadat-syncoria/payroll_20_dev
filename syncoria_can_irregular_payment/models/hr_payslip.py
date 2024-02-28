from odoo import fields, models, api, _


class VacationHrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    irregular_pay_req_ref = fields.Char('Irregular Pay', readonly=True, default="")


class IrregularPayslip(models.Model):
    _inherit = 'hr.payslip'

    # def _calculate_irregular_pay(self, employee,irre_pay_ids):
    #
    #     amount = self.amount
    #
    #     return amount

    def compute_sheet(self):
        for rec in self:
            bonus_input_type = rec.env.ref('syncoria_can_irregular_payment.input_ca_bonus_pay').id
            retro_input_type = rec.env.ref('syncoria_can_irregular_payment.input_ca_retro_pay').id
            payslips = rec.filtered(lambda slip: slip.state in ['draft', 'verify'])
            for payslip in payslips:
                try:
                    des_name = ","
                    employee_id = payslip.employee_id
                    irregular_employee_wise_pay_ids = payslip.env['employee.wise.irregular.pay'].search(
                        [('employee_id', '=', employee_id.id), ('pay_status', '=', False)]).filtered(
                        lambda x: x.irr_pay_id.state == 'validate' and payslip.date_to >= x.irr_pay_id.date )
                    if irregular_employee_wise_pay_ids:
                        payslip.input_line_ids.filtered(
                            lambda x: x.input_type_id.id in [bonus_input_type, retro_input_type]).unlink()
                # HASH use
                    irregular_type_wise = {
                        "bonus": {'input_type_id': bonus_input_type, 'name': '', 'irregular_pay_req_ref': '',
                                  'amount': 0.0},
                        "retro": {'input_type_id': retro_input_type, 'name': '', 'irregular_pay_req_ref': '',
                                  'amount': 0.0},
                    }
                    for ir_pay in irregular_employee_wise_pay_ids:
                        irre_pay_id = ir_pay.irr_pay_id
                        if irre_pay_id.payment_type == 'bonus':
                            irregular_type_wise['bonus']['name'] = irregular_type_wise['bonus']['name']+des_name.join(
                                ir_pay.mapped('irr_pay_id.description'))
                            irregular_type_wise['bonus']['irregular_pay_req_ref'] =irregular_type_wise['bonus']['irregular_pay_req_ref']+ des_name.join(
                                ir_pay.mapped('irr_pay_id.name'))
                            irregular_type_wise['bonus']['amount'] += abs(ir_pay.amount)
                        elif irre_pay_id.payment_type == 'retro':
                            irregular_type_wise['retro']['name'] =  irregular_type_wise['retro']['name']+des_name.join(
                                ir_pay.mapped('irr_pay_id.description') )
                            irregular_type_wise['retro']['irregular_pay_req_ref'] = irregular_type_wise['retro']['irregular_pay_req_ref']+des_name.join(
                                ir_pay.mapped('irr_pay_id.name') )
                            irregular_type_wise['retro']['amount'] += abs(ir_pay.amount)


                    if not irregular_employee_wise_pay_ids:
                        payslip.input_line_ids.filtered(
                            lambda x: x.input_type_id.id in [bonus_input_type, retro_input_type]).unlink()
                    else:
                        inputs_line = []
                        if irregular_type_wise['bonus']['amount']>0.0:
                            inputs_line.append((0, 0, {
                            'input_type_id': bonus_input_type,
                            'name': irregular_type_wise['bonus']['name'] or "",
                            'irregular_pay_req_ref': irregular_type_wise['bonus']['irregular_pay_req_ref'] or "",
                            'amount': irregular_type_wise['bonus']['amount'] or 0.0,
                        }))
                        if irregular_type_wise['retro']['amount'] > 0.0:
                            inputs_line.append((0, 0, {
                            'input_type_id': retro_input_type,
                            'name': irregular_type_wise['retro']['name'] or "",
                            'irregular_pay_req_ref': irregular_type_wise['retro']['irregular_pay_req_ref'] or "",
                            'amount': irregular_type_wise['retro']['amount'] or "",
                        }))


                        payslip.write({'input_line_ids': inputs_line})
                except Exception as e:
                    payslip.message_post(body=f"Irregular Pay Error:{e}")

        return super(IrregularPayslip, self).compute_sheet()

    def action_payslip_paid(self):

        # [FIX ME] Must optimise code(Very bad  coding)

        res = super(IrregularPayslip, self).action_payslip_paid()
        bonus_input_type = self.env.ref('syncoria_can_irregular_payment.input_ca_bonus_pay').id
        retro_input_type = self.env.ref('syncoria_can_irregular_payment.input_ca_retro_pay').id
        employee_wise_irregular_pay_req = self.env['employee.wise.irregular.pay']
        for rec in self:
            if rec.state == 'paid':
                bonus_pay_input_line_ids = rec.input_line_ids.filtered(lambda x: x.input_type_id.id == bonus_input_type)
                bonus_pay_req_ids = bonus_pay_input_line_ids.irregular_pay_req_ref.split(
                    ',') if bonus_pay_input_line_ids.irregular_pay_req_ref else []
                for bonus_pay in bonus_pay_req_ids:
                    ir_id = employee_wise_irregular_pay_req.search(
                        [('irr_pay_id', '=', bonus_pay), ('employee_id', '=', rec.employee_id.id)], limit=1)
                    if ir_id:
                        ir_id.write({
                            'pay_status': True
                        })

                retro_pay_input_line_ids = rec.input_line_ids.filtered(lambda x: x.input_type_id.id == retro_input_type)
                retro_pay_req_ids = retro_pay_input_line_ids.irregular_pay_req_ref.split(
                    ',') if retro_pay_input_line_ids.irregular_pay_req_ref else []
                for retro_pay in retro_pay_req_ids:
                    ir_id = employee_wise_irregular_pay_req.search(
                        [('irr_pay_id', '=', retro_pay), ('employee_id', '=', rec.employee_id.id)], limit=1)
                    if ir_id:
                        ir_id.write({
                            'pay_status': True
                        })

        return res
