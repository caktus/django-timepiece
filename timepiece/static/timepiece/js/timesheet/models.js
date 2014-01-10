var Entry = Backbone.Model.extend({
    sync: function(method, model, options) {
        options || (options = {});
        options.error = handleAjaxFailure;

        switch (method) {
            case "delete":
                options.url = model.get('get_delete_url');
                break;
            case "update":
                options.url = model.get('get_edit_url');
                break;
        }

        if (options.url) {
            return Backbone.sync.call(model, method, model, options);
        }
    },

    description: function() {
        return this.get('activity__name') + " on " + this.get('project__name');
    },
    getDate: function() {
        // The "date" of this entry is tied to its end time.
        return this.getEndTime();
    },
    getDateDisplay: function() {
        var d = this.getDate();
        return days[d.getDay()] + ", " + months[d.getMonth()] + " " + d.getDate();
    },
    getEndTime: function() {
        return new Date(this.get('end_time'));
    },
    getEndTimeDisplay: function() {
        return displayTime(this.getEndTime());
    },
    getStartTime: function() {
        return new Date(this.get('start_time'));
    },
    getStartTimeDisplay: function() {
        return displayTime(this.getStartTime());
    },
    getPausedTimeDisplay: function() {
        if (this.get("paused_seconds")) {
            return formatHoursMinutes(this.get("paused_seconds"));
        }
        return "";
    },
    getTotalTimeDisplay: function() {
        return formatHoursMinutes(this.get("total_seconds"));
    },
    getStatusLabel: function() {
        // Returns nothing if this entry is unverified.
        var sts = this.get('status'),
            label = "";
        if (sts !== 'unverified') {
            cls = sts === 'verified' ? 'label label-info' : 'label label-success';
            label = $('<span />').addClass(cls);
            label.text(this.get('get_status_display'));
            label = label[0].outerHTML;
        }
        return label;
    },
    isFromCurrentMonth: function() {
        var d = this.getEndTime();
        return d >= this.weekTable.thisMonth && d <= this.weekTable.nextMonth;
    }
});

var EntryCollection = Backbone.Collection.extend({
    model: Entry,
    comparator: function(item) {
        return item.getDate();
    }
});
