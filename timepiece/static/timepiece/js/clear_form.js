jQuery(function($){
    $(document).ready(function() {
        form_list = $('input#id_date_form_clear_btn');
        if (form_list.length > 0){
            form_list.click(function() {
                $("ul#ledger-date-fieldlist input[type='text']").each(function() {
                    $(this).val('');
                });
            });
        }
    });
});
