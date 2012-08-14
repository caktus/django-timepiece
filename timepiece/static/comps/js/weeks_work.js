




function ProgressBar(loc, width, height, label) {
    this.loc = loc;
    this.width = width;
    this.height = height;
    this.label = label;

    // Settings
    this.draw_width = this.width - 10; // Draw inside the svg without clipping
    this.edge_offset = 5; // Come off the edge

    // Append our svg for drawing
    this.chart = d3.select(loc).append('svg')
        .attr('width', this.draw_width)
        .attr('class', 'hoursChart');
}

ProgressBar.prototype.draw = function(hours_worked, hours_remaining, hours_over) {
    var width = this.draw_width,
        offset = 0;

    // Calculate offset before drawing border
    // If we have a label to draw, decrease the width, draw the label,
    // and set the offset to the amount width was decreased
    if(this.label) {
        offset = 200;
        width -= offset;

        this.chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#000000')
            .attr('font-weight', 'bolder')
            .attr('x', 0)
            .attr('y', 30)
            .text(this.label);
    }

    var actual_offset = offset + this.edge_offset;

    this.border = this.chart
        .append('rect')
        .attr('x', actual_offset).attr('y', 0)
        .attr('height', this.height)
        .attr('width', width - 10); // Prevent border clipping

    var bar = this,
        chart = this.chart,
        total = hours_worked + hours_remaining;

    // Draw the hours worked bar first
    bar.worked = chart.append('rect')
        .style('stroke-width', '0px')
        .style('stroke', 'none')
        .attr('class', 'workedHours')
        .attr('height', this.height - 1)
        .attr('y', 1).attr('x', actual_offset + 1);  // Account for stroke

    // Color the worked bar red if there are overworked hours
    var worked_color = 'steelblue';
    if (hours_over > 0) {
        worked_color = 'indianred';
    }

    // Correct width of the worked bar if there is no remaining bar
    var worked_width = (hours_worked / total) * width - this.edge_offset;
    if (hours_remaining <= 0) {
        worked_width = worked_width - this.edge_offset - 1;
    }

    bar.worked.transition()
        .delay(100)
        .duration(750)
        .attr('width', worked_width)
        .style('fill', worked_color)
        .each('end', drawRemaining);

    // Draw the remaining bar after drawing the worked bar
    function drawRemaining() {
        bar.remaining = chart.append('rect')
            .style('stroke-width', '0px')
            .style('stroke', 'none')
            .style('fill', 'gray')
            .attr('class', 'remainingHours')
            .attr('height', 39)
            .attr('y', 1)
            .attr('x', Number(d3.select(this).attr('x')) + Number(d3.select(this).attr('width')));

        bar.remaining.transition()
            .delay(100)
            .duration(750)
            .attr('width', (hours_remaining / total) * width - bar.edge_offset - 1)
            .each('end', drawText);
    }

    // Calculate the correct positioning
    function textPosition(bar, text) {
        var box = text.node().getBBox();

        var xpos = Number(bar.attr('x')) +
            Number(bar.attr('width')) / 2 - box.width / 2;
        
        var ypos = Number(bar.attr('height')) / 2 + box.height / 4;

        return {
            'x': xpos,
            'y': ypos
        };
    }

    // Display text after the bars have been drawn
    function drawText() {
        var worked_text = hours_worked + ' worked';
        if (hours_over > 0) {
            worked_text += ' (' + hours_over + ' over)';
        }
        var worked = chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#FFFFFF')
            .attr('font-weight', 'bolder')
            .text(worked_text);

        var worked_pos = textPosition(bar.worked, worked);

        worked.attr('x', worked_pos.x)
            .attr('y', worked_pos.y);

        // Only display remaining text if there are remaining hours
        if (hours_remaining > 0) {
            var remaining = chart.append('text')
                .attr('font-size', '16px')
                .attr('fill', '#FFFFFF')
                .attr('font-weight', 'bolder')
                .text(hours_remaining + ' remaining');
        
            var rem_pos = textPosition(bar.remaining, remaining);

            remaining.attr('x', rem_pos.x)
                .attr('y', rem_pos.y);
        }
    }
};

(function() {
    bar_width = $('.bar').width();

    new ProgressBar('#hours1.bar', bar_width, 40).draw(27.73, 40, 0);
    new ProgressBar('#hours2.bar', bar_width, 40, 'django-timepiece').draw(10, 0, 2)
    new ProgressBar('#hours3.bar', bar_width, 40, 'Cotton University').draw(10.73, 4.27, 0);
    new ProgressBar('#hours4.bar', bar_width, 40, 'Dimagi SOW').draw(7, 10, 0);
}());
