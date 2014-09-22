/**
 * File activating any jQuery UI or Bootstrap widgets
 */

$(function() {
    /* use jQuery-UI to apply a date picker to all crm-date-fields.  If you
     * wish, substitute your JavaScript library of choice.
     */
    $('[name*=date][name!=week_update],#id_start_time_0,#id_end_time_0,#id_week_start,#id_scheduled,#id_response_required_by_0').datepicker({
        'dateFormat': 'yy-mm-dd'  /* yy = 4 digit year, believe it or not */
    });
});
