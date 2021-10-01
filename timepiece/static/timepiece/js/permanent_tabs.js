// JavaScript to create permanent links to Bootstrap tabs.
// When the user clicks on another tab, the browser location
// will change without reloading the page.
//
// The code expects that basePath, tabIds, and defaultTab have been defined.

function changeActiveTab(to) {
    // Change active tab.
    $('.nav-tabs li.active').removeClass('active');
    $('.nav-tabs a[to=' + to + ']').parent().addClass('active');

    // Change active tab content.
    $('.tab-pane.active').removeClass('active');
    $('.tab-pane#' + to).addClass('active');
}


$(function () {
    // Called when the user moves through browser history.
    window.onpopstate = function(event) {
        var path = window.location.pathname,
            to = defaultTab;
        if (path.indexOf(basePath) > -1) {
            var tail = path.substring(basePath.length),
                parts = tail.split('/');
            if (parts.length <= 2 && tabIds.indexOf(parts[0]) > -1) {
                to = parts[0];
            }
        }
        changeActiveTab(to);
    };

    // Called when the user clicks on a tab link.
    $('.tab-link').click(function(event) {
        event.preventDefault();
        self = $(this);
        if (!self.parent().hasClass('active')) {
            var to = self.attr('to'),
                search = window.location.search;
            history.pushState({}, '', basePath + to + '/' + search);
            changeActiveTab(to);
        }
        if( stickyHeader !== undefined){
            calculateHeaderCutoffs();
            calculateColumnCutoffs();
        }
    });
});

