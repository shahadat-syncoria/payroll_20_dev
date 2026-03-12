/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { markup } from "@odoo/owl";
import { PayslipBatchFormController } from "@hr_payroll/views/payslip_run_form/hr_payslip_run_form";

patch(PayslipBatchFormController.prototype ,{
    async selectEmployees() {

        const pay_cycle = this.model.root.data.pay_cycle || false;
        const pay_cycle_period = this.model.root.data.pay_cycle_period?.id || false;

        const employeeListAction = await this.orm.call(
            "hr.payslip.run",
            "action_payroll_hr_version_list_view_payrun_cus",
            [
                [this.model.root.resId],
                serializeDate(this.model.root.data.date_start),
                serializeDate(this.model.root.data.date_end),
                this.model.root.data.structure_id?.id,
                this.model.root.data.company_id?.id,
                pay_cycle,

            ]
        );
        console.log("this.model.root.resId", this.model.root.resId)
        return this.actionService.doAction({
            ...employeeListAction,
            context: {
                ...(employeeListAction.context || {}),
                date_start: this.model.root.data.date_start,
                date_end: this.model.root.data.date_end,
                pay_cycle_period:this.model.root.data.pay_cycle_period,
                raw_record: this.model.root.data,
            },
        });

    },
});
