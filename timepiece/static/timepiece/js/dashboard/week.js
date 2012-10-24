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

function createLabel(name, assigned) {
    return $('<div />', {
        'text': name + ' - ' + humanizeTime(assigned) + ' assigned'
    });
}

// Creates all bar elements for the given progress div.
function createBars(progress, worked, assigned) {
    // Worked bar.
    if (worked > 0 && assigned > 0) {
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
    }

    // Overtime bar.
    if (worked > assigned) {
        var overtime_percent = Math.min(1, 1 - assigned / worked),
            overtime_text = humanizeTime(worked - assigned) + ' Over';
        overtime_percent = Math.ceil(overtime_percent * 100);
        progress.append(createBar('danger', overtime_percent, overtime_text));
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


var container = $('#week-hours'),
    data = JSON.parse(container.attr('data'));

// Create overall progress bar.
var progress_all = createProgress('progress-all');
createBars(progress_all, data.worked, data.assigned);
container.append(progress_all);

// Create individual project progress bars.
var max = Math.max(data.projects[0].worked, data.projects[0].assigned);
for (var i = 0; i < data.projects.length; i++) {
    var project = data.projects[i],
        progress = createProgress('progress-' + project.pk),
        percent = Math.min(1, Math.max(project.worked, project.assigned) / max);

    var thing = $('<div />', {
        'style': 'width: ' + Math.floor(percent * 100) + '%;'
    })
    createBars(progress, project.worked, project.assigned);
    thing.append(createLabel(project.name, project.assigned));
    thing.append(progress);
    container.append(thing);
}
