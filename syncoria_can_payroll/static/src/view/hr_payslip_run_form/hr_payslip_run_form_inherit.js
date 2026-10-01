/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { markup } from "@odoo/owl";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";
import { PayslipBatchFormController } from "@hr_payroll/views/payslip_run_form/hr_payslip_run_form";

// Odoo 20: the pay run form is a "create" dialog (the record is not saved yet), so the server
// method is called on an empty recordset. Same flow as the core `selectEmployees`, plus the pay cycle.
patch(PayslipBatchFormController.prototype, {
    selectEmployees() {
        return executeButtonCallback(this.ui.activeElement, async () => {
            const isValid = await this.model.root.checkValidity({ displayNotification: true });
            if (!isValid) {
                return;
            }
            const data = this.model.root.data;
            const payCycle = data.pay_cycle
                ? { id: data.pay_cycle.id, display_name: data.pay_cycle.display_name }
                : false;
            const payCyclePeriod = data.pay_cycle_period
                ? { id: data.pay_cycle_period.id, display_name: data.pay_cycle_period.display_name }
                : false;

            const employeeListAction = await this.orm.call(
                "hr.payslip.run",
                "action_payroll_hr_version_list_view_payrun_cus",
                [
                    [],
                    serializeDate(data.date_start),
                    serializeDate(data.date_end),
                    data.structure_id?.id,
                    data.company_id?.id,
                    payCycle ? payCycle.id : false,
                    data.employee_type_ids?._currentIds || [],
                ]
            );

            // plain serializable snapshot (the record itself has circular references)
            const rawRecord = {
                date_start: data.date_start,
                date_end: data.date_end,
                structure_id: data.structure_id
                    ? { id: data.structure_id.id, display_name: data.structure_id.display_name }
                    : false,
                company_id: data.company_id?.id || false,
                employee_type_ids: data.employee_type_ids?._currentIds || [],
                pay_cycle: payCycle,
                pay_cycle_period: payCyclePeriod,
                pay_cycle_year: data.pay_cycle_year || null,
            };

            return this.actionService.doAction({
                ...employeeListAction,
                help: markup(employeeListAction.help),
                context: {
                    hide_off_cycle_btn: true,
                    raw_record: rawRecord,
                    payrun_date_start: serializeDate(data.date_start),
                    payrun_date_end: serializeDate(data.date_end),
                    date_start: serializeDate(data.date_start),
                    date_end: serializeDate(data.date_end),
                    pay_cycle: payCycle,
                    pay_cycle_period: payCyclePeriod,
                },
            });
        });
    },
});
