
// Shorten the node's text if it is too wide
function shortenText(node, max_width, partial_allowed) {
    if (node.node() === null) { return node; }

    var box;
    // First try shortening the text to fit inside the box.
    if (partial_allowed === true) {
        box = node.node().getBBox();
        if (box.width > max_width) {
            var sub = Math.floor(max_width / box.width * node.text().length) - 3,
                name = jQuery.trim(node.text().substring(0, sub)) + '...';
            node.text(name);
        } else { return node; }
    }

    // Truncate text to '...' if still too wide.
    box = node.node().getBBox();
    if (box.width > max_width) {
        node.text('...');
    } else { return node; }

    // Fully truncate text if it is still too wide.
    box = node.node().getBBox();
    if (box.width > max_width) {
        node.text('');
    }

    return node;
}

function getHours(time) {
    return Math.floor(time);
}

function getMinutes(time) {
    return Math.floor((time - getHours(time)) * 60);
}

function humanizeTime(time) {
    var hours = getHours(time);
        minutes = getMinutes(time);

    humanized_time = hours + 'h';
    if (minutes > 0) {
        humanized_time += ' ' + minutes + 'm';
    }
    return humanized_time;
}
