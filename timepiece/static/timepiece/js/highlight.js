var getRow = function(cell, table) {
    return cell.parent().find('td, th');
}


var getCol = function(cell, table) {
    var i = cell.index() + 1;
    return table.find('td:nth-child(' + i + '), th:nth-child(' + i + ')');
}


var _isNotHighlighted = function(index, cell) {
    return !$(cell).hasClass('hover');
};


// Returns whether all cells in the group are highlighted.
var isCompletelyHighlighted = function(cells) {
    return !cells.filter(_isNotHighlighted).length;
}


// Within the given tableSelector, highlight the current row & column when
// hovering over a cell.
var hoverToHighlight = function(tableSelector) {
    $(tableSelector).delegate('td, th', 'mouseover mouseout', function(event) {
        var cell = $(this),
            table = cell.closest(tableSelector),
            row = getRow(cell, table),
            col = getCol(cell, table),
            toggle = event.type === 'mouseover';

        row.toggleClass('hover', toggle);
        col.toggleClass('hover', toggle);
    });
};


// Within the given tableSelector, highlight the current row & column when
// a cell is clicked. If the cell is clicked again, the highlight is removed.
var clickToHighlight = function(tableSelector) {
    $(tableSelector).delegate('td, th', 'click', function(event) {
        var cell = $(this),
            table = cell.closest(tableSelector),
            row = getRow(cell, table),
            col = getCol(cell, table);


        // If the cell was the last one highlighed, remove all highlight
        // from the table and return.
        if (isCompletelyHighlighted(row) && isCompletelyHighlighted(col)) {
            table.find('td, th').removeClass('hover');
            return;
        }

        table.find('td, th').removeClass('hover');
        row.addClass('hover');
        col.addClass('hover');
    });
}
