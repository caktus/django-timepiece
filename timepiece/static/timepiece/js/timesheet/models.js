var Entry = Backbone.Model.extend({
    sync: function(method, model, options) {
        options || (options = {});
        options.error = handleAjaxFailure;

        switch (method) {
            case "delete":
                options.url = model.get('get_ajax_delete_url');
                break;
        }

        if (options.url) {
            return Backbone.sync.call(model, method, model, options);
        }
    },

    description: function() {
        return this.get('activity__name') + " on " + this.get('project__name');
    },
    get_date: function() {
        // The "date" of this entry is tied to its end time.
        return this.get_end_time();
    },
    get_date_display: function() {
        var d = this.get_date();
        return days[d.getDay()] + ", " + months[d.getMonth()] + " " + d.getDate();
    },
    get_end_time: function() {
        return new Date(this.get('end_time'));
    },
    get_end_time_display: function() {
        return displayTime(this.get_end_time());
    },
    get_start_time: function() {
        return new Date(this.get('start_time'));
    },
    get_start_time_display: function() {
        return displayTime(this.get_start_time());
    },
    get_status_label: function() {
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
        var d = this.get_end_time();
        return d >= this.weekTable.thisMonth && d <= this.weekTable.nextMonth;
    }
});

var EntryCollection = Backbone.Collection.extend({
    model: Entry,
    comparator: function(item) {
        return item.get_date();
    }
});
