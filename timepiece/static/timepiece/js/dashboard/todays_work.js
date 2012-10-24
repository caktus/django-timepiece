var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var get_time_display = function(stamp) {
    var dt = new Date(stamp);
    var period = dt.getHours() < 12 ? 'AM' : 'PM';
    var hours = dt.getHours() > 12 ? dt.getHours() - 12 : dt.getHours();
    if (hours === 0) {
        hours = 12;
    }
    var minutes = dt.getMinutes() < 10 ? '0' + dt.getMinutes() : dt.getMinutes();
    return hours + ':' + minutes + ' ' + period;
};

function Timeline(loc, start_time, end_time, width, height) {
    this.loc = loc;
    this.width = width;
    this.height = height;

    this.container = d3.select(this.loc).append('svg');

    // Settings
    var today = new Date();
    today.setHours(0),
    today.setMinutes(0),
    today.setSeconds(0),
    today.setMilliseconds(0);
    today = today.getTime();
    this.draw_width = this.width - 40; // Draw inside the svg without clipping
    this.y_offset = 20; // Height offset from time marker
    var one_hour = 60 * 60 * 1000; // One hour in milliseconds
    var default_start = (one_hour * 8) + today;
        default_end = (one_hour * 18) + today;
    this.interval = one_hour;

    /*
    Set the start and end times to defaults (8AM - 6PM) unless entries fall
    outside of this, in which case round to the nearest hour on the outside.
    */
    if (start_time < default_start) {
        this.start_time = Math.floor(start_time / one_hour) * one_hour;
    } else {
        this.start_time = default_start;
    }

    if (end_time > default_end) {
        this.end_time = Math.ceil(end_time / one_hour) * one_hour;
    } else {
        this.end_time = default_end;
    }

    var span_in_hours = (this.end_time - this.start_time) / one_hour,
        width_span_ratio = Math.ceil(this.draw_width / span_in_hours);
    /*
    If the browser is small enough or more than a day has elapsed, show six
    time interval markers
    */
    if (width_span_ratio < 60 || span_in_hours > 24) {
        this.interval = Math.floor((span_in_hours * one_hour) / 5);
    }
    this.edge_offset = 20; // Come off the edge
}

Timeline.prototype.draw = function() {
    var dt = this.end_time - this.start_time;

    this.line_offset = this.draw_width / (dt / this.interval);

    for(var i = 0; i <= dt / this.interval; i++) {
        var x_offset = i * this.line_offset + this.edge_offset;

        this.container.append('line')
            .attr('x1', x_offset).attr('x2', x_offset)
            .attr('y1', this.y_offset).attr('y2', this.height - this.y_offset)
            .style('stroke', '#000000');

        var time = get_time_display(new Date(this.start_time + this.interval * i));

        this.container.append('text')
            .attr('x', x_offset - 15).attr('y', 10)
            .style('font-size', '10px')
            .style('fill', '#000000')
            .style('opacity', 1)
            .text(time);
    }
};

function Entry(timeline, entry_data) {
    this.project_name = entry_data['project_name'];
    this.start_time = entry_data['start_time'];
    this.end_time = entry_data['end_time'];
    this.hours = entry_data['hours'];
    this.pk = entry_data['pk'];
    this.update_url = entry_data['update_url'];
    this.active = entry_data['active'];
    this.seconds_paused = entry_data['seconds_paused'];

    this.timeline = timeline;

    this.height = timeline.height - 2 * timeline.y_offset;
}

Entry.prototype.draw = function() {
    var timeline = this.timeline;

    var dt = this.end_time - this.start_time,
        width = timeline.line_offset * (dt / timeline.interval),
        x_offset = timeline.line_offset *
            (this.start_time - timeline.start_time) / timeline.interval  + timeline.edge_offset;

    var entry = timeline.container.append('rect')
        .attr('x', x_offset).attr('y', timeline.y_offset + 5)
        .attr('rx', 10).attr('ry', 10)
        .attr('height', this.height - 10)
        .attr('width', width);

    // Add the attributes for popovers
    var popover_msg = 'You have worked ' + this.hours + ' hours.';
    var start_str = get_time_display(new Date(this.start_time));
    var end_str = get_time_display(new Date(this.end_time));
    popover_msg += '<br/>' + start_str + ' - ' + end_str;
    entry.attr('data-title', this.project_name)
        .attr('data-content', popover_msg);

    entry.transition()
        .delay(100)
        .duration(1500)
        .attr('fill', '#0061AA')
        .attr('stroke', '#333333')
        .attr('stroke-width', '2px')
        .style('opacity', '0.95');

    var text = timeline.container.append('text')
        .attr('font-weight', 'bolder')
        .style('font-size', '14px')
        .text(this.project_name);

    // Get bounding boxes for centering text
    var text_box = text.node().getBBox(),
        entry_box = entry.node().getBBox();
    
    // Strip project name down if its too large
    if(text_box.width > entry_box.width) {
        var sub = Math.ceil(text_box.width / (text_box.width - entry_box.width)), // Ratio using widths
            name = this.project_name.substring(0, sub) + '...';

        name = sub === 0 || entry_box.width < 30 ? '' : name;

        text.text(name);

        // New bounding box
        text_box = text.node().getBBox();
    }

    // Do some positioning to get the text centered correctly
    var text_xpos = x_offset + width / 2 - text_box.width / 2,
        text_ypos = timeline.y_offset + this.height / 2 + text_box.height / 4;

    text.attr('x', text_xpos)
        .attr('y', text_ypos);
    
    // Display!
    text.transition()
        .delay(100)
        .duration(1500)
        .attr('fill', '#FFFFFF')
        .style('opacity', '1.0');

    // Handle click
    var that = this;
    $(entry.node()).click(function() {
        location.href = that.update_url;
    });
};

var draw_timeline = function(data) {
    var $timeline = $('#timeline'),
        height = $timeline.height(),
        width = $(window).width();

    var start_time = new Date(data.start_time),
        end_time = new Date(data.end_time);

    // Convert the minutes to milliseconds
    var timezone_offset = start_time.getTimezoneOffset() * 60 * 1000;

    var t = new Timeline($timeline.selector, start_time.getTime() + timezone_offset,
        end_time.getTime() + timezone_offset, width, height);
    t.draw();

    for(var i = 0; i < data.entries.length; i++) {
        var entry = data.entries[i],
            start = new Date(entry.start_time),
            end = new Date(entry.end_time);

        var dt = end - start,
            hours = Math.ceil((dt / (3600 * 1000)) * 100) / 100;

        var e = new Entry(t, {
            'start_time': start.getTime() + timezone_offset,
            'end_time': end.getTime() + timezone_offset,
            'project_name': entry.project,
            'pk': entry.pk,
            'active': entry.active,
            'seconds_paused': entry.seconds_paused,
            'hours': hours,
            'update_url': entry.update_url
        });
        e.draw();
    }

    // Enable popovers
    $('.timeline rect').popover({
        'placement': 'top',
        'trigger': 'hover'
    });
};


(function() {
    var data = JSON.parse(script.getAttribute('data-entries'));
    draw_timeline(data);

    $(window).resize(function() {
        $('#timeline svg').remove();
        draw_timeline(data);
    });
})();
