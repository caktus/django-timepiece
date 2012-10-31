
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

// Label for project charts.
function createProjectLabel(project_name, assigned) {
    return $('<div />', {
        'class': 'progress-label',
        'text': project_name + ' - ' + humanizeTime(assigned) + ' Assigned'
    });
}

// Worked, remaining, or overtime hours on a project.
function createBar(type, percent, label) {
    var cls = (type === 'remaining') ? type : 'bar bar-' + type;
    return $('<div />', {
        'class': cls,
        'style': 'width: ' + percent + '%;',
        'text': label
    });
}

// Container for all bars (worked, overtime, remaining) on a project.
function createChart(worked, assigned) {
    var chart = $('<div />', {
        'class': 'progress'
    });

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
        worked_percent = Math.floor(worked_percent * 100);
        chart.append(createBar('success', worked_percent, worked_text));  // Green
    }

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked),
            overtime_text = humanizeTime(worked - assigned) + ' Overtime';
        overtime_percent = Math.ceil(overtime_percent * 100);
        chart.append(createBar('danger', overtime_percent, overtime_text));  // Red
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = Math.min(1, 1 - worked / assigned),
            remaining_text = humanizeTime(assigned - worked) + ' Remaining';
        remaining_percent = Math.ceil(remaining_percent * 100);
        chart.append(createBar('remaining', remaining_percent, remaining_text));  // Blue
    }

    return chart;
}

// Entry point for creating overall progress chart.
(function() {
    var container = $('#progress-all'),
        worked = parseFloat(container.attr('data-worked')),
        assigned = parseFloat(container.attr('data-assigned'));

    var overall_chart = createChart(worked, assigned);
    container.append(overall_chart);
})();
