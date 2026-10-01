/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";
import { VersionPayrunListController } from "@hr_payroll/views/payslip_run_version_list/hr_version_list_controller";

patch(VersionPayrunListController.prototype, {
    buildRawRecord(rawRecord) {
        // core clean fields + our pay cycle fields, always as scalar values
        return {
            ...super.buildRawRecord(rawRecord),
            pay_cycle: rawRecord.pay_cycle?.id || false,
            pay_cycle_period: rawRecord.pay_cycle_period?.id || false,
            pay_cycle_year: rawRecord.pay_cycle_year || null,
        };
    },

    async onSelect() {
        // adding employees to an existing pay run keeps the core behaviour
        if (this.props.context?.payrun_id) {
            return super.onSelect(...arguments);
        }
        // new pay run: open the manual input wizard for the selected employees
        this.state.disabled = true;
        try {
            const selectedEmployeeIds = await this.model.root.getResIds(true);
            const ctx = this.props.context || {};
            const action = await this.orm.call("hr.payslip.run", "action_open_manual_wizard_from_list", [
                [],
                selectedEmployeeIds,
            ]);
            return this.actionService.doAction({
                ...action,
                help: action.help ? markup(action.help) : action.help,
                context: {
                    ...(action.context || {}),
                    raw_record: ctx.raw_record,
                    date_start: ctx.date_start,
                    date_end: ctx.date_end,
                    pay_cycle_period: ctx.pay_cycle_period,
                    pay_cycle: ctx.pay_cycle,
                },
            });
        } finally {
            this.state.disabled = false;
        }
    },
});
