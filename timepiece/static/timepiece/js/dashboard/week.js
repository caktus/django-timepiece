
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


var build_project_bar = function($bar_cell, percentage) {
    var $bar = $('<div />');
    /*
    Find sprite_num, which is 0 to 5 (inclusive) and determines what sprite
    class to use
    */
    var sprite_divisor = 4, // number of ways to divide progress by 100
        sprite_quotient = (100 / sprite_divisor),
        sprite_num = Math.round(percentage / sprite_quotient);
    if (percentage > 100) {
        sprite_num = sprite_divisor + 1; // assign to the overworked sprite
    }
    // Use sprite_num to assign a class with the appropriate sprite
    var sprite_class;
    switch(sprite_num) {
        case 0:
            sprite_class = 'sprite-0'; break;
        case 1:
            sprite_class = 'spirte-25'; break;
        case 2:
            sprite_class = 'sprite-50'; break;
        case 3:
            sprite_class = 'sprite-75'; break;
        case 4:
            sprite_class = 'sprite-100'; break;
        case 5:
            sprite_class = 'sprite-over'; break;
    }
    $bar.addClass(sprite_class);
    // Append the new bar div to the container
    $bar_cell.append($bar);
};


// Entry point to create overall progress chart and per project progress bars
(function() {
    var container = $('#progress-all'),
        worked = parseFloat(container.attr('data-worked')),
        assigned = parseFloat(container.attr('data-assigned'));

    var overall_chart = createChart(worked, assigned);
    container.append(overall_chart);

    // Create progress bars for each project
    $.each($('.project_progress_bar'), function() {
        var self = $(this);
        var worked = self.data('worked'),
            assigned = self.data('assigned');
        // Set percentage to 100 for unassigned projects.
        var percentage = (assigned === 0) ? 100: (worked / assigned) * 100;
        // Getting around .toFixed() implicit conversion to a string
        percentage *= 100;
        percentage = Math.round(percentage);
        percentage /= 100;
        // Attach progress bar sprite
        build_project_bar(self, percentage);
    });
})();
