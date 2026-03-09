/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { markup } from "@odoo/owl";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { VersionPayrunListController } from "@hr_payroll/views/payslip_run_version_list/hr_version_list_controller";


patch(VersionPayrunListController.prototype, {
    buildRawRecord(rawRecord) {
        // Original clean fields from parent
        const result = super.buildRawRecord(rawRecord);

        // Add your fields, but always convert to SCALAR values only
        return {
            ...result,

            // your custom fields
            pay_cycle: rawRecord.pay_cycle?.id || false,
            pay_cycle_period: rawRecord.pay_cycle_period?.id || false,
            pay_cycle_year: rawRecord.pay_cycle_year || null,
        };
    },
    async selectEmployees() {
        const versionIds = this.model.root.selection.map(r => r.resId);

        const employeeIds = await this.orm.call(
            "hr.version",
            "read",
            [versionIds, ["employee_id"]]
        );

        const selectedEmployeeIds = employeeIds.map(r => r.employee_id[0]);
        const payslipRunId = this.props.context.payslip_run_id;

        if (!selectedEmployeeIds.length) {
            return this.displayNotification({
                type: "warning",
                message: "Please select at least one employee.",
            });
        }

        const employeeListAction = await this.orm.call(
            "hr.payslip.run",
            "action_open_manual_wizard_from_list",
            [
                [this.model.root.resId],
                selectedEmployeeIds,

            ]
        );

        // ✅ MERGE context instead of overwriting
        return this.actionService.doAction({
            ...employeeListAction,
            help: markup(employeeListAction.help),
            context: {
                ...(employeeListAction.context || {}),
                raw_record: this.model.root.data,
                date_start: this.props.context.date_start,
                date_end: this.props.context.date_end,
                pay_cycle_period:this.props.context.pay_cycle_period
            },
        });
    }


});


