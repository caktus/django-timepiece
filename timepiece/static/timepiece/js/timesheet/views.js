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
            success: function(deletedModel, response) {
                showSuccess(deletedModel.description() + " has been deleted.");
                for (var i=0; i < deletedModel.weekTable.models.length; i++) {
                    var model = deletedModel.weekTable.models[i];
                    if (model.get('id') == deletedModel.get('id')) {
                        deletedModel.weekTable.models.splice(i, 1);
                        break;
                    }
                }
            }
        });
        this.$el.remove();  // TODO: move this to success function.
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

var WeekTable = Backbone.View.extend({
    tagName: "div",
    initialize: function() {
        this.models = this.options['models'];
        this.weekStart = this.options['weekStart'];
        this.weekEnd = this.options['weekEnd'];
        this.thisMonth = this.options['thisMonth'];
        this.lastMonth = this.options['lastMonth'];
        this.nextMonth = this.options['nextMonth'];
    },
    events: {
        "click .btn[title='Approve Week']": "approveWeek",
        "click .btn[title='Reject Week']": "rejectWeek",
        "click .btn[title='Verify Week']": "verifyWeek"
    },
    render: function() {
        this.$el.addClass('week');
        this.$el.append($(_.template($('#week-template').html(), {
            weekStart: this.weekStart,
            weekEnd: this.weekEnd
        })));
        this.totalHours = 0;
        _.each(this.models, function(entry) {
            var row = new EntryRow({ model: entry });
            this.totalHours += entry.get('total_seconds');
            row.render().$el.insertBefore(this.$el.find('tbody tr.week-summary'));
        }, this);
        this.$el.find('.week-summary .total-hours').text(this.totalHours);
        return this;
    },

    approveWeek: function(event) {
        event.preventDefault();
        var msg = "All verified entries from this week are now approved.",
            entryIds = getIdsFromCurrentMonth(this.models);
        approveEntries(this.collection, entryIds, msg);
    },
    rejectWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now unverified.",
            entryIds = getIdsFromCurrentMonth(this.models);
        rejectEntries(this.collection, entryIds, msg);
    },
    verifyWeek: function(event) {
        event.preventDefault();
        var msg = "All entries from this week are now verified.",
            entryIds = getIdsFromCurrentMonth(this.models);
        verifyEntries(this.collection, entryIds, msg);
    }
});

var Timesheet = Backbone.View.extend({
    el: $("html"),
    initialize: function() {
        // Create a table view for each week of the month.
        this.weekTables = [];
        _.each(this.options['weekRanges'], function(range) {
            this.weekTables.push(new WeekTable({
                collection: this.collection,  // Pass for reference.
                models: [],  // The entries which are a part of the week.
                thisMonth: this.options['thisMonth'],
                nextMonth: this.options['nextMonth'],
                lastMonth: this.options['lastMonth'],
                weekStart: new Date(range[0]),
                weekEnd: new Date(range[1])
            }));
        }, this);

        // Split entries by week.
        // (Assumes that entries are in ascending order by end_time.)
        var weekCursor = entryCursor = 0;
        for (entryCursor; entryCursor < this.collection.length;) {
            if (weekCursor >= this.weekTables.length) { break; }

            var weekTable = this.weekTables[weekCursor],
                entry = this.collection.at(entryCursor);
                date = new Date(entry.get('end_time'));

            if (date > weekTable.weekEnd) { weekCursor++; }
            else if (date < weekTable.weekStart) { entryCursor++; }
            else {
                entry.weekTable = weekTable;  // Store table on entry.
                weekTable.models.push(entry);
                entryCursor++;
            }
        }

        // Render the table for each week.
        _.each(this.weekTables, function(weekTable) {
            $('#all-entries').append(weekTable.render().el);
        }, this)
    },
    events: {
        "click .btn[title='Verify All']": "verifyMonth",
        "click .btn[title='Approve All']": "approveMonth",
        "click .btn[title='Reject All']": "rejectMonth",
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
    approveMonth: function(event) {
        event.preventDefault();
        var msg = "All verified entries from this month are now approved.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        approveEntries(this.collection, entryIds, msg);
    },
    rejectMonth: function(event) {
        event.preventDefault();
        var msg = "All entries from this month are now unverified.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        rejectEntries(this.collection, entryIds, msg);
    },
    verifyMonth: function(event) {
        event.preventDefault();
        var msg = "All entries from this month are now verified.",
            entryIds = getIdsFromCurrentMonth(this.collection.toArray());
        verifyEntries(this.collection, entryIds, msg);
    }
});
