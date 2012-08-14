var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var data = JSON.parse(script.getAttribute('data-entries'));

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

ProgressBar.prototype.draw = function(hours_worked, hours_remaining, hours_over, total_hours) {
    var width = this.draw_width,
        offset = 0;
    var title = this.label;

    // Calculate offset before drawing border
    // If we have a label to draw, decrease the width, draw the label,
    // and set the offset to the amount width was decreased
    if(title) {
        offset = 200;
        width -= offset;

        var text = this.chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#000000')
            .attr('font-weight', 'bolder')
            .attr('x', 0)
            .attr('y', 30)
            .text(title);

        // Truncate the label if it is too long
        var text_box = text.node().getBBox();
        if (text_box.width > offset) {
            var sub = Math.floor(offset / text_box.width * title.length) - 3,
                name = jQuery.trim(title.substring(0, sub)),
                name = name + '...';
            text.text(name);
            text_box = text.node().getBBox();
        }
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

    // Add the attributes for popovers
    var worked_title = (title ? title : 'Total') + ' - Worked';
    var worked_message = 'You have worked ' + hours_worked + ' hours out of ' + total_hours + ' hours scheduled';
    if (hours_over > 0) {
        worked_message += ', including ' + hours_over + ' hours overtime.';
    } else {
        worked_message += '.';
    }
    bar.worked.attr('data-title', worked_title)
        .attr('data-content', worked_message);

    // Color the worked bar red if there are overworked hours
    var worked_color = hours_over <= 0 ? '#0061aa' : 'indianred';

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

        // Add the attributes for popovers
        var remaining_title = (title ? title : 'Total') + ' - Remaining';
        var remaining_message = 'You have ' + hours_remaining + ' hours remaining.';
        bar.remaining.attr('data-content', remaining_message)
            .attr('data-title', remaining_title);

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

        truncateText(worked, bar.worked);

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
   
            truncateText(remaining, bar.remaining);
 
            var rem_pos = textPosition(bar.remaining, remaining);
    
            remaining.attr('x', rem_pos.x)
                .attr('y', rem_pos.y);
        }
        
        $('.hoursChart rect').popover({
            'placement': 'top'
        });
    }

    // Truncate text if it is too wide
    function truncateText(text_node, bar_node) {
        var text_box = text_node.node().getBBox();
        var bar_box = bar_node.node().getBBox();
        if (text_box.width > bar_box.width) {
            text_node.text('...');
            text_box = text_node.node().getBBox();
            if (text_box.width > bar_box.width) {
                text_node.text('');
            }
        }
    }
};

(function() {
    bar_width = $('.bar').width();

    var total_hours = parseFloat(data.total_hours);
    var worked = parseFloat(data.worked);
    var remaining = parseFloat(data.remaining);
    var overworked = parseFloat(data.overworked);
    new ProgressBar('#all-hours.bar', bar_width, total_hours).draw(worked, remaining, overworked, total_hours);

    for(var i = 0; i < data.projects.length; i++) {
        var project = data.projects[i];
        var proj_hours = parseFloat(project.total_hours);
        var worked = parseFloat(project.worked);
        var remaining = parseFloat(project.remaining);
        var overworked = parseFloat(project.overworked);
        var id = '#hours-' + project.pk + '.bar';
        new ProgressBar(id, bar_width, total_hours, project.name).draw(worked, remaining, overworked, proj_hours);
    }

}());
