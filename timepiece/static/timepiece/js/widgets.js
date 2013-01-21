/**
 * File activating any jQuery UI or Bootstrap widgets
 */

$(function() {
    /* use jQuery-UI to apply a date picker to all crm-date-fields.  If you
     * wish, substitute your JavaScript library of choice.
     */
    $('[name*=date][name!=week_update],#id_start_time_0,#id_end_time_0,#id_week_start').datepicker({
        'dateFormat': 'yy-mm-dd'  /* yy = 4 digit year, believe it or not */
    });

    $('#popover-toggle').popover({
        'title': function() {
            var target = $(this).data('target');

            return $(target).children('.popover-title').html();
        },
        'content': function() {
            var target = $(this).data('target');

            return $(target).children('.popover-content').html();
        },
        'placement': 'bottom',
        'trigger': 'hover'
    });
});
