var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var data = JSON.parse(script.getAttribute('data-entries'));

function ProgressBar(container, width, height, label) {
    this.width = width;
    this.height = height;
    this.label = label;

    this.edge_offset = 5;  // Come off the edge.
    this.draw_width = this.width - 2 * this.edge_offset;  // Draw inside the svg without clipping

    // Append our svg for drawing
    this.chart = d3.select(container).append('svg')
        .attr('width', this.draw_width)
        .attr('class', 'hoursChart');
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
        color_remaining = 'gray';

    // If we have a label to draw, increase the bar offset, decrease the bar
    // width, and draw the label.
    if (label) {
        offset = 200;
        width -= offset;

        var text = this.chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#000000')
            .attr('font-weight', 'bolder')
            .attr('x', 0)
            .attr('y', 30)
            .text(label)
            .attr('class', 'project-label')
            .attr('data-title', label);

        // Shorten the label if it is too long.
        shortenText(text, offset, true);
    }

    offset = offset + edge_offset;

    // Container for worked/remaining hours.
    this.border = this.chart
        .append('rect')
        .attr('x', offset)
        .attr('y', 1)
        .attr('height', height)
        .attr('width', width - 2 * edge_offset)  // Prevent border clipping.
        .style('stroke-width', '2px')
        .style('stroke', '#333333');

    // Draw the hours worked bar first
    bar.worked = chart.append('rect')
        .attr('class', 'workedHours')
        .attr('height', height - 2)
        .attr('x', offset + 1)  // Account for stroke
        .attr('y', 2);
//        .style('stroke-width', '0px')
//        .style('stroke', 'none')

    // Add the attributes for popovers
    var worked_title = (label || 'Total') + ' - Worked',
        worked_message = 'You have worked ' + humanizeTime(hours_worked) + ' hours out of ' + humanizeTime(hours_assigned) + ' hours scheduled';
    if (hours_overworked > 0) {
        worked_message += ', including ' + humanizeTime(hours_overworked) + ' hours overtime.';
    } else {
        worked_message += '.';
    }
    bar.worked.attr('data-title', worked_title)
        .attr('data-content', worked_message);

    // Color the bar based on whether there are overworked hours
    var worked_color = hours_overworked <= 0 ? color_worked : color_overworked;

    // Determine width of worked bar & correct width if there is no remaining bar
    var ratio = hours_assigned > 0 ? hours_worked / hours_assigned : 1,
        worked_width = ratio * width - edge_offset;
    if (hours_remaining <= 0) {
        worked_width = worked_width - edge_offset - 1;
    }

    if (hours_remaining <= 0) {
        bar.worked.transition()
            .delay(100)
            .duration(1500)
            .attr('width', worked_width - 1)
            .style('fill', worked_color)
            .style('opacity', opacity)
            .each('end', drawText);
    } else {
        bar.worked.transition()
            .delay(100)
            .duration(750)
            .attr('width', worked_width - 1)
            .style('fill', worked_color)
            .style('opacity', opacity)
            .each('end', drawRemaining);
    }

    // Draw the remaining bar after drawing the worked bar
    function drawRemaining() {
        bar.remaining = chart.append('rect')
            .style('fill', color_remaining)
            .style('opacity', opacity)
            .attr('class', 'remainingHours')
            .attr('height', height - 2)
            .attr('y', 2)
            .attr('x', Number(d3.select(this).attr('x')) + Number(d3.select(this).attr('width')) - 1);

        // Add the attributes for popovers
        var remaining_title = (label || 'Total') + ' - Remaining',
            remaining_message = 'You have ' + humanizeTime(hours_remaining) + ' hours remaining.';
        bar.remaining.attr('data-content', remaining_message)
            .attr('data-title', remaining_title);

        bar.remaining.transition()
            .delay(0)
            .duration(750)
            .attr('width', (hours_remaining / hours_assigned) * width - edge_offset)
            .each('end', drawText);
    }

    // Calculate the correct positioning.
    function textPosition(bar, text) {
        var box = text.node().getBBox(),
            xpos = Number(bar.attr('x')) + Number(bar.attr('width')) / 2 - box.width / 2,
            ypos = (Number(bar.attr('height')) / 2) + (box.height / 4) + 2;

        return {
            'x': xpos,
            'y': ypos
        };
    }

    // Display text after the bars have been drawn.
    function drawText() {
        var worked_text = humanizeTime(hours_worked) + ' worked';
        if (hours_overworked > 0) {
            worked_text += ' (' + humanizeTime(hours_overworked) + ' over)';
        }
        var worked = chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#FFFFFF')
            .attr('font-weight', 'bolder')
            .text(worked_text);

        shortenText(worked, bar.worked.node().getBBox().width, false);

        var worked_pos = textPosition(bar.worked, worked);

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

            var rem_pos = textPosition(bar.remaining, remaining);
            remaining.attr('x', rem_pos.x)
                .attr('y', rem_pos.y);
        }

        // Finally, activate popovers and tooltips.
        $('.hoursChart rect').popover({'placement': 'top'});
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
