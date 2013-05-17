/*
IMPORTANT: Some ad block extensions prevent the browser from loading
Javascript files with 'doubleclick' in the name.
/

$(function() {
    /*
    Prevents double-click of a form submit button by disabling the
    button and adding the 'disabled' class. Assumes that the name of
    the submit button is submit. Usage:
        <form action="" method="post" class="prevent-doubleclick">
            <input type="submit" name="submit" value="Submit! />
        </form>
    */
    $('form.prevent-doubleclick').submit(function() {
        var submit = $(this.submit);
        submit.attr({
            value: 'Submitting...',
            disabled: 'disabled'
        });
        submit.addClass('disabled');
        submit.text('Submitting...');
        return true;
    });

    /*
    Prevents double-click of a link by disabling the link and adding
    the 'disabled' class. Usage:
        <a href="/" class="prevent-doubleclick">Click here!</a>
    */
    $('a.prevent-doubleclick').one('click', function() {
        var self = $(this);
        self.click(function() { return false; });
        self.addClass('disabled');
        self.text('Submitting...');
        return true;
    });
});
