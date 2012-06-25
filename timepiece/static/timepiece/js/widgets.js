/**
 * File activating any jQuery UI or Bootstrap widgets
 */

jQuery(function($) {
    /* use jQuery-UI to apply a date picker to all crm-date-fields.  If you
     * wish, substitute your JavaScript library of choice.
     */
    $('[name*=date],#id_start_time_0,#id_end_time_0').datepicker({
        'dateFormat': 'mm/dd/yy'
    });
});