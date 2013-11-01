var EntryRow = Backbone.View.extend({
    tagName: "tr",
    initialize: function() {
        this.listenTo(this.model, "change", this.render);
    },
    events: {
        "click a[title='Delete']": "deleteEntry",
        "click a[title='Verify']": "verifyEntry",
        "click a[title='Approve']": "approveEntry",
        "click a[title='Reject']": "rejectEntry"
    },
    render: function() {
        if (!this.model.isFromCurrentMonth()) {
            this.$el.addClass('muted')
                    .attr({
                'data-toggle': 'tooltip',
                'title': 'You cannot edit an entry from another month.'
            });
        }
        template = _.template($('#entry-row-template').html(), { model: this.model });
        this.$el.html(template);
        return this;
    },

    approveEntry: function(event) {
        event.preventDefault();
        if (this.model.isFromCurrentMonth()) {
            approveEntries(this.model.collection, [this.model.get("id")]);
        } else {
            showError("You can't edit an entry from another month.");
        }
    },
    deleteEntry: function() {
        event.preventDefault();
        this.model.destroy({
            success: function(model, response) {
                showSuccess(model.description() + " has been deleted.");
            }
        });
        this.$el.remove();  // TODO: move this to success function.
        // FIXME: the EntryWeekTable with this row retains the reference
        // to it and therefore you can't verify/approve/reject by week
        // after deleting an entry from it (but you can by month).
    },
    rejectEntry: function(event) {
        event.preventDefault();
        if (this.model.isFromCurrentMonth()) {
            rejectEntries(this.model.collection, [this.model.get("id")]);
        } else {
            showError("You can't edit an entry from another month.");
        }
    },
    verifyEntry: function(event) {
        event.preventDefault();
        if (this.model.isFromCurrentMonth()) {
            verifyEntries(this.model.collection, [this.model.get("id")]);
        } else {
            showError("You can't edit an entry from another month.");
        }
    }
});

var EntryWeekTable = Backbone.View.extend({
    tagName: "div",
    initialize: function() {
        this.weekGroup = this.options.weekGroup;
        this.$el.addClass('week');
        this.$el.append($(_.template($('#week-template').html(), {
            weekStart: this.options.weekStart,
            weekEnd: this.options.weekEnd
        })));
        this.totalHours = 0;
        _.each(this.weekGroup, function(entry) {
            var row = new EntryRow({ model: entry });
            this.totalHours += entry.get('total_seconds');
            row.render().$el.insertBefore(this.$el.find('tbody tr.week-summary'));
        }, this);
        this.$el.find('.week-summary .total-hours').text(this.totalHours);
    },
    events: {
        "click .btn[title='Approve Week']": "approveWeek",
        "click .btn[title='Reject Week']": "rejectWeek",
        "click .btn[title='Verify Week']": "verifyWeek"
    },
    render: function() {
        return this;
    },

    approveWeek: function(event) {
        event.preventDefault();
        var msg = "All verified entries from this week are now approved.",
            entryIds = getIdsFromCurrentMonth(this.weekGroup);
        approveEntries(this.collection, entryIds, msg);
    },
    rejectWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now unverified.",
            entryIds = getIdsFromCurrentMonth(this.weekGroup);
        rejectEntries(this.collection, entryIds, msg);
    },
    verifyWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now verified.",
            entryIds = getIdsFromCurrentMonth(this.weekGroup);
        verifyEntries(this.collection, entryIds, msg);
    }
});

var Timesheet = Backbone.View.extend({
    el: $("html"),
    initialize: function() {
        this.allEntries = $('#all-entries');
        this.weekGroups = [];

        // Split entries into groups by week.
        _.each(weeks, function(week) {
            this.weekGroups.push([new Date(week[0]), new Date(week[1]),[]]);
        }, this);
        var weekCursor = entryCursor = 0, _collection = this.collection.toArray();
        for (entryCursor; entryCursor < _collection.length;) {
            if (weekCursor >= weeks.length) {
                break;
            }
            var weekStart = new Date(weeks[weekCursor][0]),
                weekEnd = new Date(weeks[weekCursor][1]),
                entry = _collection[entryCursor],
                date = new Date(entry.get('end_time'));
            if (date > weekEnd) {
                weekCursor++;
            } else if (date < weekStart) {
                entryCursor++;
            } else {
                this.weekGroups[weekCursor][2].push(entry);
                entryCursor++;
            }
        }

        // Render each week group.
        _.each(this.weekGroups, function(group) {
            var weekTable = new EntryWeekTable({
                weekStart: group[0],
                weekEnd: group[1],
                weekGroup: group[2],
                collection: this.collection
            });
            this.allEntries.append(weekTable.render().el);
        }, this)
    },
    events: {
        "click .btn[title='Verify All']": "verifyAll",
        "click .btn[title='Approve All']": "approveAll",
        "click .btn[title='Reject All']": "rejectAll",
        //"change #filter-entries select": "filterEntries"
    },
    render: function() {
        return this;
    },
    /*
    filterEntries: function(event) {
        entryStatus = event.currentTarget.value;
        var coll;
        if (entryStatus !== "") {
            this.filter = {'status': entryStatus};
            coll = this.collection.where(this.filter);
        } else {
            coll = this.collection.toArray();
        }
        this.table.empty();
        _.each(coll, function(entry) {
            var view = new EntryRow({ model: entry });
            this.table.append(view.render().el);
        }, this)
    },
    */
    approveAll: function(event) {
        event.preventDefault();
        var msg = "All verified entries from this month are now approved.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        approveEntries(this.collection, entryIds, msg);
    },
    rejectAll: function(event) {
        event.preventDefault();
        var msg = "All entries from this month are now unverified.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        rejectEntries(this.collection, entryIds, msg);
    },
    verifyAll: function(event) {
        event.preventDefault();
        var msg = "All entries from this month are now verified.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        verifyEntries(this.collection, entryIds, msg);
    }
});
