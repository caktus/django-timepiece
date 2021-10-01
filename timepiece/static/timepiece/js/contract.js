// Progress bars for contract page

// Worked, remaining, or overtime hours.
function createBar(type, percent) {
    return $('<div />', {
        'class': 'contract-progress ' + type,
        'style': 'width: ' + percent + '%;'
    });
}

function createProgressChart(fraction, full_width) {
    // full_width is the fraction of the time that should take up the
    // full column. E.g. if full_width is 2.0 and we're at 100% of scheduled
    // time, the time bar should go half-way across the column.

    var chart = $('<div class="progress contract-progress" style="display: block"/>');

    var type;
    if (fraction <= 0.90) {
      type = 'bar bar-worked';
    } else if (fraction <= 1.0) {
      type = 'bar bar-yellow';
    } else {
      type = 'bar bar-red';
    }
    var bar = createBar(type, 100.0 * fraction);
    chart.append(bar);
    if (fraction < 1.0) {
      // add `remaining` bar out to 1.0
      chart.append(createBar('remaining', 100.0 * (1.0 - fraction)));
    }

    // size of the bar we're using out of the whole column
    var cutoff = Math.max(1.0, fraction);  // max data we're displaying - at least 1.0, maybe more
    chart.attr('style', 'width: ' + (100*cutoff/full_width) + '%');

    return chart;
}

// Entry point to create per-contract progress charts.
$(function() {
    // Create progress bars for each contract
    // what fraction should we represent as the full width of the column?
    var full_width = Math.max(1.0, max_schedule_fraction, max_work_fraction);

    $.each($('.project-bar'), function() {
        var self = $(this),
            fraction = self.data('fraction');

        self.append(createProgressChart(fraction, full_width));
    });
});
