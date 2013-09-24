
// Given a table selector, highlight the current row & column
// on hover.
function hover_highlight(table_selector) {
    $(table_selector).delegate('td, th', 'mouseover mouseout', function(event) {
        var self = $(this),  // <td> or <th> element
            num = self.index() + 1,
            toggle = event.type === 'mouseover',
            table = self.closest(table_selector);
        self.parent().find('td, th').toggleClass('hover', toggle);
        table.find('td:nth-child(' + num + ')').toggleClass('hover', toggle);
        table.find('th:nth-child(' + num + ')').toggleClass('hover', toggle);
    });
};
