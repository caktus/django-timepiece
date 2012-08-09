function ProgressBar(loc, width, height, label) {
    Rectangle.call(this, loc, width, height);

    this.label = label;
}

ProgressBar.prototype = new Rectangle();
ProgressBar.prototype.constructor = ProgressBar;

ProgressBar.prototype.draw = function(worked, remaining) {
    var width = $(this.loc).width(),
        offset = 0;

    // Calculate offset before drawing border
    // If we have a label to draw, decrease the width, draw the label,
    // and set the offset to the amount width was decreased
    if(this.label) {
        width -= 200;
        offset = 200;

        this.chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#000000')
            .attr('font-weight', 'bolder')
            .attr('x', 0)
            .attr('y', 30)
            .text(this.label);
    }

    Rectangle.prototype.draw.call(this, offset);

    var bar = this,
        chart = this.chart,
        total = worked + remaining;

    bar.worked = chart.append('rect')
        .style('stroke-width', '0px')
        .style('stroke', 'none')
        .attr('class', 'workedHours')
        .attr('height', this.height - 1)
        .attr('y', 1).attr('x', offset);

    bar.worked.transition()
        .delay(100)
        .duration(750)
        .attr('width', (worked / total) * width)
        .style('fill', 'steelblue')
        .each('end', drawRemaining);

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
            .attr('width', (remaining / total) * width)
            .each('end', drawText);
    }

    function drawText() {
        var text_width = 30;

        chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#FFFFFF')
            .attr('font-weight', 'bolder')
            .attr('x', function() {
                return Number(bar.worked.attr('x')) + Number(bar.worked.attr('width')) / 2 - text_width;
            })
            .attr('y', Number(bar.worked.attr('height')) / 2 + 7)
            .text(worked + ' worked');

        chart.append('text')
            .attr('font-size', '16px')
            .attr('fill', '#FFFFFF')
            .attr('font-weight', 'bolder')
            .attr('x', function() {
                return Number(bar.remaining.attr('x')) + Number(bar.remaining.attr('width')) / 2 - text_width;
            })
            .attr('y', Number(bar.remaining.attr('height')) / 2 + 7)
            .text(remaining + ' remaining');
    }
};

ProgressBar.prototype.addRemainingHours = function(first_argument) {
    // body...
};

(function() {
    bar_width = $('.bar').width();

    new ProgressBar('#hours1.bar', bar_width, 40).draw(19, 40);
    new ProgressBar('#hours2.bar', bar_width, 40, 'django-timepiece').draw(2, 8);
    new ProgressBar('#hours3.bar', bar_width, 40, 'CBS Local Places').draw(5, 19);
    new ProgressBar('#hours4.bar', bar_width, 40, 'Awesomesauce 3000').draw(12, 13);
}());
