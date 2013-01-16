// General-purpose utilities that are useful across the site.


$(function() {
    // Adds a GET parameter, next, containing the current location.
    $('a.redirect-next').click(function(event) {
        event.preventDefault();

        var link = $(this).attr('href')
        if (link.indexOf('?') == -1) {  // The link has no GET params.
            link += '?'
        } else {  // Add another GET param to the link.
            link += '&'
        }

        var next = window.location.pathname + window.location.search,
            next = encodeURIComponent(next);
        window.location.href = link + 'next=' + next;
    });
});
