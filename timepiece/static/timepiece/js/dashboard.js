
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

// If any hours have been worked, the progress displayed will be a minimum of
// 1%. If worked and assigned are both 0, only the overtime bar will display.
function createProgressChart(worked, assigned) {
    // Prevent negative time.
    worked = Math.max(worked, 0);
    assigned = Math.max(assigned, 0);

    var chart = $('<div class="progress" />'),
        worked_percent = 0;

    // Worked bar.
    if (worked > 0 && assigned > 0) {  // Skip if only remaining or overtime bar is needed.
        var worked_text;
        if (worked <= assigned) {
            worked_percent = Math.min(1, worked / assigned);
            worked_text = humanizeTime(worked) + ' Worked';
        } else {
            worked_percent = Math.min(1, assigned / worked);
            worked_text = humanizeTime(assigned) + ' Worked';
        }
        worked_percent = Math.floor(worked_percent * 100);
        worked_percent = Math.max(1, worked_percent)  // Display minimum of 1%.
        chart.append(createBar('bar bar-worked', worked_percent, worked_text));
    }

    // Overtime bar.
    if (worked >= assigned) {
        var overtime_percent = 100 - worked_percent,
            overtime_text = humanizeTime(worked - assigned) + ' Overtime';
        chart.append(createBar('bar bar-overtime', overtime_percent, overtime_text));
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = 100 - worked_percent,
            remaining_text = humanizeTime(assigned - worked) + ' Remaining';
        chart.append(createBar('remaining', remaining_percent, remaining_text));
    }

    return chart;
}

// Entry point to create overall progress chart and per-project progress charts.
$(function() {
    var container = $('#overall-bar'),
        worked = parseFloat(container.attr('data-worked')),
        assigned = parseFloat(container.attr('data-assigned'));
    container.append(createProgressChart(worked, assigned));

    // Create progress bars for each project
    $.each($('.project-bar'), function() {
        var self = $(this),
            worked = self.data('worked'),
            assigned = self.data('assigned'),
            local_max = Math.max(worked, assigned),
            width = Math.min(100, local_max / max_hours * 100),
            bar = createProgressChart(worked, assigned);

        bar.attr('style', 'width: ' + width + '%');
        self.append(bar);
    });
});
