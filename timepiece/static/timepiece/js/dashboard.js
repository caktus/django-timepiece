
function getHours(time) {
    return Math.floor(time);
}

function getMinutes(time) {
    var minutes = Math.floor((time - getHours(time)) * 60);
    if (minutes < 10) {
        minutes = '0' + minutes;
    }
    return minutes
}

function humanizeTime(time) {
    var hours = getHours(time),
        minutes = getMinutes(time);

    return hours + ':' + minutes;
}

// Worked, remaining, or overtime hours.
function createBar(type, percent, label) {
    return $('<div />', {
        'class': type,
        'style': 'width: ' + percent + '%;',
        'text': label
    });
}

function createOverallProgress(worked, assigned) {
    var chart = $('<div class="progress" />');

    // Worked bar.
    if (worked > 0 && assigned > 0) {  // Skip if only remaining or overtime bar is needed.
        var worked_percent, worked_text;
        if (worked <= assigned) {
            worked_percent = Math.min(1, worked / assigned);
            worked_text = humanizeTime(worked) + ' Worked';
        } else {
            worked_percent = Math.min(1, assigned / worked);
            worked_text = humanizeTime(assigned) + ' Worked';
        }
        worked_percent = Math.floor(worked_percent.toFixed(5) * 100);
        chart.append(createBar('bar bar-success', worked_percent, worked_text));
    }

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked),
            overtime_text = humanizeTime(worked - assigned) + ' Overtime';
        overtime_percent = Math.ceil(overtime_percent.toFixed(5) * 100);
        chart.append(createBar('bar bar-danger', overtime_percent, overtime_text));
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = Math.min(1, 1 - worked / assigned),
            remaining_text = humanizeTime(assigned - worked) + ' Remaining';
        remaining_percent = Math.ceil(remaining_percent.toFixed(5) * 100);
        chart.append(createBar('remaining', remaining_percent, remaining_text));
    }

    return chart;
}


function createProjectProgress(worked, assigned) {
    var chart = $('<div class="progress-wrapper" />');

    // Worked bar.
    if (worked > 0 && assigned > 0) {  // Skip if only overtime bar is needed.
        var worked_percent;
        if (worked <= assigned) {
            worked_percent = Math.min(1, worked / assigned);
        } else {
            worked_percent = Math.min(1, assigned / worked);
        }
        worked_percent = Math.floor(worked_percent.toFixed(5) * 100);
        chart.append(createBar('worked', worked_percent, '&nbsp'));
    }

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked);
        overtime_percent = Math.ceil(overtime_percent.toFixed(5) * 100);
        chart.append(createBar('overtime', overtime_percent, '&nbsp'));
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = Math.min(1, 1 - worked / assigned);
        remaining_percent = Math.ceil(remaining_percent.toFixed(5) * 100);
        chart.append(createBar('remaining', remaining_percent, '&nbsp'));
    }

    return chart;
}


// Entry point to create overall progress chart and per-project progress charts
(function() {
    var container = $('#overall-bar'),
        worked = parseFloat(container.attr('data-worked')),
        assigned = parseFloat(container.attr('data-assigned'));
    container.append(createOverallProgress(worked, assigned));

    // Create progress bars for each project
    $.each($('.project-bar'), function() {
        var self = $(this),
            worked = self.data('worked'),
            assigned = self.data('assigned'),
            local_max = Math.max(worked, assigned),
            width = Math.min(100, local_max / max_hours * 100),
            bar = createProjectProgress(worked, assigned);

        bar.attr('style', 'width: ' + width + '%');
        self.append(bar);
    });
})();
