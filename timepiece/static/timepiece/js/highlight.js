var _getRow = function(cell, table) {
    return cell.parent().find('td, th');
}


var _getCol = function(cell, table) {
    var i = cell.index() + 1;
    return table.find('td:nth-child(' + i + '), th:nth-child(' + i + ')');
}


// Within the given tableSelector, highlight the current row & column when
// hovering over a cell.
var hoverToHighlight = function(tableSelector) {
    $(tableSelector).delegate('td, th', 'mouseover mouseout', function(event) {
        var cell = $(this),
            toggle = event.type === 'mouseover',
            table = cell.closest(tableSelector);
        _getRow(cell, table).toggleClass('hover', toggle);
        _getCol(cell, table).toggleClass('hover', toggle);
    });
};


// Within the given tableSelector, highlight the current row & column when
// a cell is clicked. If the cell is clicked again, the highlight is removed.
var clickToHighlight = function(tableSelector) {
    $(tableSelector).delegate('td, th', 'click', function(event) {
        var cell = $(this),
            table = cell.closest(tableSelector),
            row = _getRow(cell, table),
            col = _getCol(cell, table);

        // If the cell is highlighted, check to see if its row & column are
        // the ones that are currently highlighted.
        if (cell.hasClass('hover')) {
            var isNotHighlighted = function(index, cell) {
                return !$(cell).hasClass('hover')
            };

            // Check if the row & column have no cells that are unhighlighted.
            if (!row.filter(isNotHighlighted).length &&
                !col.filter(isNotHighlighted).length) {
                // Remove all highlights & return.
                table.find('td, th').removeClass('hover');
                return;
            }
        }

        table.find('td, th').removeClass('hover');
        row.addClass('hover');
        col.addClass('hover');
    });
}
