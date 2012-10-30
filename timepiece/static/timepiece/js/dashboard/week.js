
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
function createChart(id, worked, assigned, percent) {
    var chart = $('<div />', {
        'id': id,
        'class': 'progress',
        'style': 'width: ' + percent + '%;'
    });

    // Worked bar.
    if (worked > 0 && assigned > 0) {  // Shortcut if only remaining or overtime bar is needed.
        var worked_percent, worked_text;
        if (worked <= assigned) {
            worked_percent = Math.min(1, worked / assigned);
            worked_text = humanizeTime(worked);
        } else {
            worked_percent = Math.min(1, assigned / worked);
            worked_text = humanizeTime(assigned);
        }
        worked_percent = Math.floor(worked_percent * 100);
        chart.append(createBar('success', worked_percent, worked_text));  // Green
    }

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked),
            overtime_text = humanizeTime(worked - assigned);
        overtime_percent = Math.ceil(overtime_percent * 100);
        // Only show a red bar if the user is assigned and went over.
        var bar_type;
        if (assigned > 0) {
            bar_type = 'danger';  // Red
            overtime_text += ' Over';
        } else {
            bar_type = 'success';  // Green
        }
        chart.append(createBar(bar_type, overtime_percent, overtime_text));
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = Math.min(1, 1 - worked / assigned),
            remaining_text = humanizeTime(assigned - worked) + ' Remaining';
        remaining_percent = Math.ceil(remaining_percent * 100);
        chart.append(createBar('info', remaining_percent, remaining_text));  // Blue
    }

    return chart;
}

// Entry point for creating progress charts for overall & individual projects.
(function() {
    var container = $('#week-hours'),
        data = JSON.parse(container.attr('data'));

    var overall_chart = createChart('progress-all', data.worked, data.assigned, 100);
    container.append(overall_chart);

    container.append('<h3>Projects</h3>');

    // Create individual project charts.
    var max = Math.max(data.projects[0].worked, data.projects[0].assigned);
    for (var i = 0; i < data.projects.length; i++) {
        var project = data.projects[i],
            portion = Math.max(project.worked, project.assigned) / max,
            percent = 100 * Math.min(1, portion),
            label = createProjectLabel(project.name, project.assigned),
            chart_id = 'progress-' + project.pk,
            chart = createChart(chart_id, project.worked, project.assigned, percent),
            progress_parent = $('<div class="progress-parent"/>')
                .append(label)
                .append(chart);
        container.append(progress_parent);
    }
})();
