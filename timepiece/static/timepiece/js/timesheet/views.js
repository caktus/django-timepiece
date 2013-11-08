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
        this.$el.addClass('week');
        this.$el.append($(_.template($('#week-template').html(), {
            weekStart: this.collection.weekStart,
            weekEnd: this.collection.weekEnd
        })));
        this.totalHours = 0;
        _.each(this.collection.toArray(), function(entry) {
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
            entryIds = getIdsFromCurrentMonth(this.collection);
        approveEntries(this.collection, entryIds, msg);
    },
    rejectWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now unverified.",
            entryIds = getIdsFromCurrentMonth(this.collection);
        rejectEntries(this.collection, entryIds, msg);
    },
    verifyWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now verified.",
            entryIds = getIdsFromCurrentMonth(this.collection);
        verifyEntries(this.collection, entryIds, msg); }
});

var Timesheet = Backbone.View.extend({
    el: $("html"),
    initialize: function() {
        var weekRanges = this.options['weekRanges'],
            entries = this.options['entries'];

        // Create an empty EntryCollection for each week of the month.
        this.weekGroups = [];
        _.each(weekRanges, function(range) {
            this.weekGroups.push(
                new EntryCollection([], {
                    thisMonth: this.options['thisMonth'],
                    nextMonth: this.options['nextMonth'],
                    lastMonth: this.options['lastMonth'],
                    weekStart: new Date(range[0]),
                    weekEnd: new Date(range[1])
                })
            );
        }, this);

        // Split entries by week.
        // Assumes that entries are in ascending order by end_time.
        var weekCursor = entryCursor = 0;
        for (entryCursor; entryCursor < entries.length;) {
            if (weekCursor >= weekRanges.length) { break; }

            var collection = this.weekGroups[weekCursor],
                entry = new Entry(entries[entryCursor]),
                date = new Date(entry.get('end_time'));

            if (date > collection.weekEnd) { weekCursor++; }
            else if (date < collection.weekStart) { entryCursor++; }
            else {
                collection.add(entry);
                entryCursor++;
            }
        }
        // Render each week group.
        _.each(this.weekGroups, function(entryCollection) {
            var weekTable = new EntryWeekTable({
                collection: entryCollection
            });
            $('#all-entries').append(weekTable.render().el);
        }, this)
    },
    events: {
        "click .btn[title='Verify All']": "verifyAll",
        "click .btn[title='Approve All']": "approveAll",
        "click .btn[title='Reject All']": "rejectAll",
        "click .btn.last-month": "",
        "click .btn.next-month": "",
        "click .btn.refresh": "",
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
