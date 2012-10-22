var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var data = JSON.parse(script.getAttribute('data-entries'));

function ProgressBar(container, width, height, label) {
    this.width = width;
    this.height = height;
    this.label = label;

    // Come off the edge.
    this.edge_offset = 5;

    // Draw inside the svg without clipping
    this.draw_width = this.width - 2 * this.edge_offset;

    // Append our svg for drawing
    this.chart = d3.select(container).append('svg')
        .attr('class', 'hoursChart')
        .attr('width', this.draw_width);
}

ProgressBar.prototype.draw = function (hours_assigned, hours_worked, hours_remaining, hours_overworked) {
    var bar = this,
        chart = this.chart,
        label = this.label,
        height = this.height,
        width = this.draw_width,
        edge_offset = this.edge_offset,
        offset = 0,

        // Styles
        opacity = 0.95,
        color_worked = '#0061aa',
        color_overworked = 'indianred',
        color_remaining = 'gray',
        color_unassigned = '#33AA33';

    // If we have a label to draw, increase the bar offset, decrease the bar
    // width, and draw the label.
    if (label) {
        offset = 200;
        width -= offset;

        var text = this.chart.append('text')
            .attr('class', 'project-label')
            .attr('data-title', label)
            .attr('fill', '#000000')
            .attr('font-size', '16px')
            .attr('font-weight', 'bolder')
            .attr('x', 0)
            .attr('y', 30)
            .text(label);

        // Shorten the label if it is too long.
        shortenText(text, offset, true);
    }

    offset += edge_offset;

    // Container for worked/remaining hours.
    this.border = this.chart.append('rect')
        .style('stroke-width', '2px')
        .style('stroke', '#333333')
        .attr('x', offset)
        .attr('y', 1)
        .attr('width', width - 2 * edge_offset)  // Prevent border clipping.
        .attr('height', height);

    // Draw the hours worked bar first.

    // Color the bar based on whether there are overworked hours.
    var worked_color = color_worked;
    if (hours_overworked > 0) {
        worked_color = hours_assigned > 0 ? color_overworked : color_unassigned;
    }

    var worked_ratio = hours_assigned > 0 ? hours_worked / hours_assigned : 1,
        worked_width = worked_ratio * width - edge_offset - 1;
    if (hours_remaining <= 0) {
        // Correct width if there is no remaining bar.
        worked_width -= (edge_offset + 1);
    }

    // Popover attributes.
    var worked_tooltip = ((label || 'Total') + ' - You have worked ' +
        humanizeTime(hours_worked));
    if (hours_overworked > 0) {
        worked_tooltip += (', including ' + humanizeTime(hours_overworked) +
            ' overtime.');
    } else {
        worked_tooltip += ' of ' + humanizeTime(hours_assigned) + ' assigned.';
    }

    bar.worked = chart.append('rect')
        .attr('class', 'workedHours')
        .attr('data-title', worked_tooltip)
        .attr('x', offset + 1)  // Account for stroke
        .attr('y', 2)
        .attr('height', height - 2);

    // Animation.
    var duration = hours_remaining <= 0 ? 1500 : 750,
        next = hours_remaining <= 0 ? drawLabel : drawRemaining;
    bar.worked.transition()
        .delay(100)
        .duration(duration)
        .attr('width', Math.max(worked_width, 0))
        .style('fill', worked_color)
        .style('opacity', opacity)
        .each('end', next);

    // Draw the remaining bar after drawing the worked bar.
    function drawRemaining() {
        var remaining_tooltip = ((label || 'Total') + ' - You have ' +
            humanizeTime(hours_remaining) + ' of ' +
            humanizeTime(hours_assigned) + ' remaining.');

        var remaining_ratio = hours_remaining / hours_assigned,
            remaining_width = remaining_ratio * width - edge_offset,
            remaining_x = (Number(d3.select(this).attr('x')) +
            Number(d3.select(this).attr('width')) - 1);
        if (hours_worked <= 0) {
            // Correct width & position if there is no worked bar.
            remaining_width -= (edge_offset + 2);
            remaining_x += 1;
        }

        bar.remaining = chart.append('rect')
            .attr('class', 'remainingHours')
            .attr('data-title', remaining_tooltip)
            .style('fill', color_remaining)
            .style('opacity', opacity)
            .attr('height', height - 2)
            .attr('x', remaining_x)
            .attr('y', 2);

        // Animation.
        bar.remaining.transition()
            .delay(0)
            .duration(750)
            .attr('width', Math.max(remaining_width, 0))
            .each('end', drawLabel);
    }

    // Display text after the bars have been drawn.
    function drawLabel() {
        var worked_text = humanizeTime(hours_worked) + ' worked';
        if (hours_overworked > 0 && hours_assigned > 0) {
            worked_text += ' (' + humanizeTime(hours_overworked) + ' over)';
        }
        var worked = chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#FFFFFF')
            .attr('font-weight', 'bolder')
            .text(worked_text);

        shortenText(worked, bar.worked.node().getBBox().width, false);

        var worked_pos = calculateLabelPosition(bar.worked, worked);

        worked.attr('x', worked_pos.x)
            .attr('y', worked_pos.y);

        // Only display remaining text if there are remaining hours.
        if (hours_remaining > 0) {
            var remaining = chart.append('text')
                .attr('font-size', '16px')
                .attr('fill', '#FFFFFF')
                .attr('font-weight', 'bolder')
                .text(humanizeTime(hours_remaining) + ' remaining');

            shortenText(remaining, bar.remaining.node().getBBox().width, false);

            var rem_pos = calculateLabelPosition(bar.remaining, remaining);
            remaining.attr('x', rem_pos.x)
                .attr('y', rem_pos.y);
        }

        // Finally, activate popovers and tooltips.
        $('.hoursChart rect').tooltip({'placement': 'top'});
        $('.project-label').tooltip({'placement': 'top'});
    }
};

(function () {
    var bar_width = $('.bar').width(),
        bar_height = 40,
        all_assigned = parseFloat(data.assigned),
        all_worked = parseFloat(data.worked),
        all_remaining = parseFloat(data.remaining),
        all_overworked = parseFloat(data.overworked),
        i;

    new ProgressBar('#all-hours.bar', bar_width, bar_height)
            .draw(all_assigned, all_worked, all_remaining, all_overworked);

    for (i = 0; i < data.projects.length; i = i + 1) {
        var project = data.projects[i],
            assigned = parseFloat(project.assigned),
            worked = parseFloat(project.worked),
            remaining = parseFloat(project.remaining),
            overworked = parseFloat(project.overworked),
            id = '#hours-' + project.pk + '.bar';
        new ProgressBar(id, bar_width, bar_height, project.name)
                .draw(assigned, worked, remaining, overworked);
    }
}());
