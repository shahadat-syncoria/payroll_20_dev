odoo.define('bambora_batch_payment.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const ajax = require('web.ajax');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const paymentBamboraMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Perform some validations for donations before performing payment
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the payment option's provider
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */

        _processPayment: function (code, paymentOptionId, flow) {
            if (code !== 'bamboraeft') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }

            if ($('.bamboraeft_form').length) {
                const errorFields = {};

                // Retrieve and store inputs
                const bamboraeftForm = document.getElementById(`o_bamboraeft_form_${paymentOptionId}`);
                const accountNumberInput = bamboraeftForm.querySelector('input[name="acc_number"]');
                const institutionNumberInput = bamboraeftForm.querySelector('input[name="institution_number"]');
                const branchNumberInput = bamboraeftForm.querySelector('input[name="branch_number"]');

                if (accountNumberInput.checkValidity()) {
                    const pattern_check_digits_between_5_12 = new RegExp(/^[0-9]{5,12}$/);
                    if (!pattern_check_digits_between_5_12.test(accountNumberInput.value)) {
                        this._displayError(
                        _t("Validation Error"),
                        _t("Bank Account Number is invalid")
                        );
                        return Promise.resolve();
                    }
                }

                if (institutionNumberInput.checkValidity()) {
                    const pattern_3_digits = new RegExp(/^[0-9]{3}$/);
                    if (!pattern_3_digits.test(institutionNumberInput.value)) {
                        this._displayError(
                        _t("Validation Error"),
                        _t("Institution Number is invalid")
                        );
                        return Promise.resolve();
                    }
                }

                if (branchNumberInput.checkValidity()) {
                    const pattern_5_digits = new RegExp(/^[0-9]{5}$/);
                    if (!pattern_5_digits.test(branchNumberInput.value)) {
                        this._displayError(
                        _t("Validation Error"),
                        _t("Bank Transit Number is invalid")
                        );
                        return Promise.resolve();
                    }
                }

                const mandatoryFields = {
                    'bank_name': _t('Bank Name'),
                    'acc_holder_name': _t('Account Holder Name'),
                    'acc_number': _t('Account Number'),
                    'bank_account_type': _t('Bank Account Type'),
                    'institution_number': _t('Institution Number'),
                    'branch_number': _t('Bank Transit Number'),
                };
                for (const id in mandatoryFields) {
                    const $field = this.$('input[name="' + id + '"],select[name="' + id + '"]');
                    $field.removeClass('is-invalid').popover('dispose');
                    if (!$field.val().trim()) {
                        errorFields[id] = _.str.sprintf(_t("Field '%s' is mandatory"), mandatoryFields[id]);
                    }
                }
                if (Object.keys(errorFields).length) {
                    for (const id in errorFields) {
                        const $field = this.$('input[name="' + id + '"],select[name="' + id + '"]');
                        $field.addClass('is-invalid');
                        $field.popover({content: errorFields[id], trigger: 'hover', container: 'body', placement: 'top'});
                        $field.data("bs.popover").config.content = errorFields[id];
                    }
                    this._displayError(
                        _t("Validation Error"),
                        _t("Some information is missing to process your payment.")
                    );
                    return Promise.resolve();
                }
            }
            return this._super(...arguments);
        },

                /**
         * Return all relevant inline form inputs based on the payment method type of the provider.
         *
         * @private
         * @param {number} providerId - The id of the selected provider
         * @return {Object} - An object mapping the name of inline form inputs to their DOM element
         */
        _getInlineFormInputs: function (providerId) {
            console.log('>>>>>>>>>>>>>>>>>>>>', this.bamboraeftInfo)
            if (this.bamboraeftInfo.payment_method_type === "card") {
                console.log('INSIDE CARD', this.bamboraeftInfo)
                return {
                    card: document.getElementById(`o_bamboraeft_card_${providerId}`),
                    month: document.getElementById(`o_bamboraeft_month_${providerId}`),
                    year: document.getElementById(`o_bamboraeft_year_${providerId}`),
                    code: document.getElementById(`o_bamboraeft_code_${acquirerId}`),
                };
            } else {
                return {
                    bankName: document.getElementById(`o_bamboraeft_bank_name_${acquirerId}`),
                    accountName: document.getElementById(`o_bamboraeft_account_name_${acquirerId}`),
                    accountNumber: document.getElementById(
                        `o_bamboraeft_account_number_${acquirerId}`
                    ),
                    institutionNumber: document.getElementById(`o_bamboraeft_institution_number_${acquirerId}`),
                    accountType: document.getElementById(`o_bamboraeft_account_type_${acquirerId}`),
                    branchNumber: document.getElementById(`o_bamboraeft_branch_number_${acquirerId}`),

                };
            }
        },

        /**
         * Return the credit card or bank data to pass to the Accept.dispatch request.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {Object} - Data to pass to the Accept.dispatch request
         */
        _getPaymentDetails: function (acquirerId) {
            const inputs = this._getInlineFormInputs(acquirerId);
            console.log('>>>>>>>>>>>>>>>>>>>>acquirerId', acquirerId, inputs)
            if (this.bamboraeftInfo.payment_method_type === 'card') {
                return {
                    cardData: {
                        cardNumber: inputs.card.value.replace(/ /g, ''), // Remove all spaces
                        month: inputs.month.value,
                        year: inputs.year.value,
                        cardCode: inputs.code.value,
                    },
                };
            } else {
                return {
                    bankData: {
                        bankName: inputs.bankName.value.substring(0, 22),
                        nameOnAccount: inputs.accountName.value.substring(0, 22), // Max allowed by acceptjs
                        accountNumber: inputs.accountNumber.value,
                        institutionNumber: inputs.institutionNumber.value,
                        accountType: inputs.accountType.value,
                        branchNumber: inputs.branchNumber.value,
                    },
                };
            }
        },

        /**
         * Prepare the inline form of Authorize.Net for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>> this', this)
            console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>> flow', flow)
            console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>> provider', provider)
            console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>> paymentOptionId', paymentOptionId)

            if (provider !== 'bamboraeft') {
                return this._super(...arguments);
            }

            // if (this.txContext.allowTokenSelection) {
            //     console.log('token');
            //     this._setPaymentFlow('token'); // No drop-in for tokens
            // } else {
            //     this._setPaymentFlow('direct');
            //     console.log('direct');
            // }
            // Check if instantiation of the drop-in is needed
            if (flow === 'token') {
                return Promise.resolve(); // No drop-in for tokens
            } else {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
            }

            this._setPaymentFlow('direct');
            console.log('flow', flow);

            return this._rpc({
                route: '/payment/bamboraeft/get_providerinfo',
                params: {
                    'providerid': paymentOptionId,
                },
            }).then(acquirerInfo => {
                console.log('>>>>>>>>>>>>>>>>>>>>>>>>>>', acquirerInfo);
                this.bamboraeftInfo = acquirerInfo;
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("An error occurred when displayed this payment form. GGGGGGGGG"),
                    error.message.data.message
                );
            });
        },


        /**
         * Checks that all payment inputs adhere to the DOM validation constraints.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {boolean} - Whether all elements pass the validation constraints
         */
        _validateFormInputs: function (acquirerId) {
            const inputs = Object.values(this._getInlineFormInputs(acquirerId));
            console.log('inputsinputsinputsinputsinputs',inputs);
            return inputs.every(element => element.reportValidity());
        },

        /**
         * Simulate a feedback from a payment provider and redirect the customer to the status page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the acquirer
         * @param {number} acquirerId - The id of the acquirer handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {Promise}
         */
        _processDirectPayment: function (provider, acquirerId, processingValues) {
            console.log('>>>>>>>>>>>>>>>>>>>>>_processDirectPayment');
            if (provider !== 'bamboraeft') {
                return this._super(...arguments);
            }

            if (!this._validateFormInputs(acquirerId)) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve();
            }
            console.log('this._getPaymentDetails(acquirerId)', this._getPaymentDetails(acquirerId), acquirerId);
            const data = {...this._getPaymentDetails(acquirerId)};
            return this._rpc({
                route: '/payment/bamboraeft/payment',
                params: {
                    'reference': processingValues.reference,
                    'data': data,
                    'providerid': acquirerId
                },
            }).then(() => {
                window.location = '/payment/status';
            });
        },

        /**
         * Redirect the customer to the status route.
         *
         * For an acquirer to redefine the processing of the payment by token flow, it must override
         * this method.
         *
         * @private
         * @param {string} provider - The provider of the token's acquirer
         * @param {number} tokenId - The id of the token handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processTokenPayment: (provider, tokenId, processingValues) => {
            // The flow is already completed as payments by tokens are immediately processed
            console.log('>>>>>>>>>>>>>>>>>>>>>_processDirectPayment', processingValues, tokenId, provider);
            if (provider !== 'bamboraeft') {
                return this._super(...arguments);
            }
            window.location = '/payment/status';
        },


    };
    checkoutForm.include(paymentBamboraMixin);
    manageForm.include(paymentBamboraMixin);
});
