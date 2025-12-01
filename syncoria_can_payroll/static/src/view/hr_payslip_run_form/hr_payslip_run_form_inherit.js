/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { markup } from "@odoo/owl";
import { PayslipBatchFormController } from "@hr_payroll/views/payslip_run_form/hr_payslip_run_form";

patch(PayslipBatchFormController.prototype ,{
    async selectEmployees() {
        console.log("✅ Patched selectEmployees with pay_cycle support -----------------------------------");

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
                this.model.root.data.pay_cycle,


            ]
        );

        return this.actionService.doAction({
            ...employeeListAction,
            help: markup(employeeListAction.help),
            context: {
                raw_record: this.model.root.data,
            },
        });
    },
});
