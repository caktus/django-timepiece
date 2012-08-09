var COLORS = {

};

function Rectangle(loc, width, height) {
    this.loc = loc;
    this.width = width;
    this.height = height;

    // Append our svg for drawing
    this.chart = d3.select(loc).append('svg')
        .attr('class', 'hoursChart');
}

Rectangle.prototype.draw = function(offset) {
    this.border = this.chart
        .append('rect')
        .attr('x', offset).attr('y', 0)
        .attr('height', this.height)
        .attr('width', this.width - offset);
};