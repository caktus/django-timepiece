function createProgress(id) {
    return $('<div />', {
        'id': id,
        'class': 'progress'
    });
}

function createBar(type, percent, label) {
    var cls = (type === 'remaining') ? 'remaining' : 'bar bar-' + type;
    return $('<div />', {
        'class': cls,
        'style': 'width: ' + percent + '%;',
        'text': label
    });
}

function createLabel(project_name, assigned) {
    return $('<div />', {
        'text': project_name + ' - ' + humanizeTime(assigned) + ' assigned'
    });
}

// Creates all bar elements for the given progress div.
function createBars(progress, worked, assigned) {
    // Early exit in case there are no hours assigned or worked
    var worked_percent, worked_text;
    if (worked <= assigned) {
        worked_percent = Math.min(1, worked / assigned);
        worked_text = humanizeTime(worked);
    } else {
        worked_percent = Math.min(1, assigned / worked);
        worked_text = humanizeTime(assigned);
    }
    worked_percent = Math.floor(worked_percent * 100);
    progress.append(createBar('success', worked_percent, worked_text));

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked),
            overtime_text = humanizeTime(worked - assigned);
        overtime_percent = Math.ceil(overtime_percent * 100);
        // Only show a red bar (danger) if the user is assigned and went over.
        var bar_type;
        if (assigned > 0) {
            bar_type = 'danger';
            overtime_text += ' Over';
        } else {
            bar_type = 'success';
        }
        progress.append(createBar(bar_type, overtime_percent, overtime_text));
    }

    // Remaining bar.
    if (worked < assigned) {
        var remaining_percent = Math.min(1, 1 - worked / assigned),
            remaining_text = humanizeTime(assigned - worked) + ' Remaining';
        remaining_percent = Math.ceil(remaining_percent * 100);
        progress.append(createBar('Remaining', remaining_percent, remaining_text));
    }
}

function getHours(time) {
    return Math.floor(time);
}

function getMinutes(time) {
    return Math.floor((time - getHours(time)) * 60);
}

function humanizeTime(time) {
    var hours = getHours(time),
        minutes = getMinutes(time),
        humanized_time = hours + ' Hours';

    if (minutes > 0) {
        humanized_time += ' ' + minutes + ' Min';
    }
    return humanized_time;
}

(function() {
    var $container = $('#week-hours'),
        data = JSON.parse($container.attr('data'));

    // Create overall progress bar.
    var progress_all = createProgress('progress-all');
    createBars(progress_all, data.worked, data.assigned);
    $container.append(progress_all);

    $container.append('<h3>Project Hours</h3>');

    // Create individual project progress bars.
    for (var i = 0; i < data.projects.length; i++) {
        var project = data.projects[i];
        if (project.worked === 0) continue;

        var $bar_parent = $('<div class="progress-parent"/>');
        var $label = $('<div class="progress-label" />')
            .append(createLabel(project.name, project.assigned));
        $bar_parent.append($label);

        var progress = createProgress('progress-' + project.pk);
        createBars(progress, project.worked, project.assigned);
        var $bar = $('<div class="progress-bar" />')
            .append(progress);
        $bar_parent.append($bar);
        $container.append($bar_parent);
    }
})();
