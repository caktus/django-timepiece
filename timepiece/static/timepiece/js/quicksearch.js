jQuery(function($) {
    $(document).ready(function() {
        $('input[name="quick_search_0"]').bind('autocompleteselect', function(e, ui) {
            $(this).parents('form').submit();
        }).bind('autocompletefocus', function(e, ui) {
            $(this).val(ui.item.value);
        });
    });
});