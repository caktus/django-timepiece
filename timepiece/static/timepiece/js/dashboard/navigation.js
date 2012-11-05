$(function() {
    $('#quick-clock-in').change(function(e) {
        var that = $(this);
        if (that.children().val()) {
            that.submit();
        }
    }); 
});