var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

//var entries = JSON.parse(script.getAttribute('data-entries'));

function Timeline(loc, start_time, end_time, width, height) {
    this.loc = loc;
    this.start_time = start_time;
    this.end_time = end_time;

    this.container = d3.select(this.loc).append('svg')
        .attr('height', height);

    this.width = width;
    this.height = height;
}

Timeline.prototype.draw = function() {
    var start_date = new Date(this.start_time),
        end_date = new Date(this.end_time),
        dt = this.end_time - this.start_time;

    var draw_width = this.width - 25; // Draw inside the svg without clipping

    var offset = 20, // Height offset from time marker
        interval = 3600000, // One hour in milliseconds
        line_offset = draw_width / (dt / interval);

    for(var i = 0; i <= dt / interval; i++) {
        var x_offset = i * line_offset + 5; // Come off of the top

        this.container.append('line')
            .attr('x1', x_offset).attr('x2', x_offset)
            .attr('y1', offset).attr('y2', this.height - offset)
            .style('stroke', '#000000');

        this.container.append('text')
            .attr('x', x_offset - 2).attr('y', 10)
            .style('font-size', '10px')
            .style('color', '#000000')
            .text(new Date(this.start_time + interval * i).getHours());
    }
};

function Entry(width, height, entry_data) {
    Rectangle.call(this, width, height);

    this.project_name = entry_data['project_name'];
    this.start_time = entry_data['start_time'];
    this.end_time = entry_data['end_time'];
    this.hours = entry_data['hours'];
    this.pk = entry_data['pk'];
}

Entry.prototype.draw = function() {
    // body...
};

(function() {
    var width = $('#timeline').width(),
        height = 100;

    d = new Date();

    new Timeline('#timeline', d.getTime() - 3600000*8, d.getTime(), width, height).draw();
}());
