var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "June",
        "July", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

// Display a message to the user.
var showMessage = function(type, message) {
    var container = $("<div />").addClass("alert alert-" + type)
    var close = $("<a />").addClass("close").attr({
        "data-dismiss": "alert",
        "href": "#"
    }).text("x");
    container.append(close).append(message);
    $("#alerts").empty().append(container);
}
var showError = function(message) { showMessage("error", message); }
var showSuccess = function(message) { showMessage("success", message); }

// Displays an error message to the user.
var handleAjaxFailure = function(xhr, status, error) {
    if (xhr.status === 400 || xhr.status === 403) {
        showError(xhr.responseText);
    } else {  // Probably a 404 or 500 error.
        showError("An internal error has occurred. Please contact an " +
                  "administrator.");
    }
}

// Calls the API to change (verify, reject, or approve) the status of
// entries.
var changeEntries = function(changeUrl, collection, entryIds, successMsg) {
    $.ajax({
        type: "POST",
        url: changeUrl,
        data: JSON.stringify(entryIds),
        dataType: "json"
    }).done(function(data, status, xhr) {
        // API returns the updated data for the changed entries.
        $(data).each(function(i, raw_entry) {
            collection.get(raw_entry.id).set(raw_entry);
        });
        showSuccess(successMsg);
    }).fail(handleAjaxFailure);
}
var verifyEntries = function(collection, entryIds, success_msg) {
    var changeUrl = verify_url;
    changeEntries(changeUrl, collection, entryIds, success_msg);
}
var rejectEntries = function(collection, entryIds, success_msg) {
    var changeUrl = reject_url;
    changeEntries(changeUrl, collection, entryIds, success_msg);
}
var approveEntries = function(collection, entryIds, success_msg) {
    var changeUrl = approve_url;
    changeEntries(changeUrl, collection, entryIds, success_msg);
}

var display_time = function(d) {
    // TODO: handle timezone.
    hours = "" + (d.getHours() % 12 || 12);
    minutes = d.getMinutes();
    minutes = minutes < 10 ? "0" + minutes : "" + minutes;
    ampm = d.getHours() >= 12 ? "pm" : "am";
    return hours + ":" + minutes + " " + ampm;
}

$(function() {
    var Entry = Backbone.Model.extend({
        description: function() {
            return this.get('activity__name') + " on " + this.get('project__name');
        },
        get_end_time: function() {
            return new Date(this.get('end_time'));
        },
        get_end_time_display: function() {
            return display_time(this.get_end_time());
        },
        get_start_time: function() {
            return new Date(this.get('start_time'));
        },
        get_start_time_display: function() {
            return display_time(this.get_start_time());
        },
        get_date: function() {
            // The "date" of this entry is tied to its end time.
            return this.get_end_time();
        },
        get_date_display: function() {
            var d = this.get_date();
            return days[d.getDay()] + ", " + months[d.getMonth()] + " " + d.getDate();
        },
        isFromCurrentMonth: function() {
            var d = this.get_end_time();
            return d >= this_month && d <= next_month;
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
        verify: function() {
            if (this.isFromCurrentMonth()) {
                msg = this.description() + " has been verified.";
                verifyEntries(this.collection, [this.get("id")], msg);
            }
        },
        approve: function() {
            if (this.isFromCurrentMonth()) {
                msg = this.description() + " has been approved.";
                approveEntries(this.collection, [this.get("id")], msg);
            }
        },
        reject: function() {
            if (this.isFromCurrentMonth()) {
                msg = this.description() + " has been rejected.";
                rejectEntries(this.collection, [this.get("id")], msg);
            }
        },
        sync: function(method, model, options) {
            options || (options = {});
            options.error = handleAjaxFailure;
            switch (method) {
                case "delete":
                    // FIXME: Entry disappears from list even if request fails???
                    options.url = api_url + '?entry_id=' + model.get('id');
                    options.success = function() {
                        showSuccess(this.description() + " has been deleted.");
                    };
                    break;
                case "update":
                    options.url = api_url + '?entry_id=' + model.get('id');
                    break;
            }
            if (options.url) {
                return Backbone.sync.call(model, method, model, options);
            }
        }
    });

    var EntryCollection = Backbone.Collection.extend({
        model: Entry,
        comparator: function(item) {
            return item.get_date();
        },
        get_current_month_ids: function() {
            var entryIds = [];
            this.each(function(entry) {
                if (entry.isFromCurrentMonth()) {
                    entryIds.push(entry.get("id"));
                }
            });
            return entryIds;
        },
        verify: function() {
            var msg = "You have verified all previously-unverified " +
                    "entries from this month.";
            verifyEntries(this, this.get_current_month_ids(), msg);
        },
        approve: function() {
            var msg = "You have approved all verified entries from this " +
                    "month.";
            approveEntries(this, this.get_current_month_ids(), msg);
        },
        reject: function() {
            var msg = "You have rejected all entries from this month. They " +
                    "are now unverified.";
            rejectEntries(this, this.get_current_month_ids(), msg);
        }
    });

    var EntryRow = Backbone.View.extend({
        tagName: "tr",
        initialize: function() {
            this.listenTo(this.model, "change", this.render);
        },
        events: {
            "click a[title=Edit]": "editEntry",
            "click a[title=Delete]": "deleteEntry",
            "click a[title=Verify]": "verifyEntry",
            "click a[title=Approve]": "approveEntry",
            "click a[title=Reject]": "rejectEntry"
        },

        editEntry: function() {
            event.preventDefault();
            // this.model.edit();
        },
        deleteEntry: function() {
            event.preventDefault();
            this.model.destroy();
            this.$el.remove();
        },
        verifyEntry: function(event) {
            event.preventDefault();
            this.model.verify();
        },
        approveEntry: function(event) {
            event.preventDefault();
            this.model.approve();
        },
        rejectEntry: function(event) {
            event.preventDefault();
            this.model.reject();
        },
        render: function() {
            if (!this.model.isFromCurrentMonth()) {
                this.$el.addClass('muted')
                        .attr({
                    'data-toggle': 'tooltip',
                    'title': 'You cannot edit an entry from another month.'
                });
            }
            template = _.template($('#entry-row').html(), {
                model: this.model
            });
            this.$el.html(template);
            return this;
        }
    });

    var EntryTable = Backbone.View.extend({
        initialize: function() {
            this.table = $(_.template($('#entry-table').html(), {}));
            _.each(this.collection, function(entry) {
                var row = new EntryRow({ model: entry });
                row.render().$el.insertBefore(this.table.find('tbody tr.week-summary'));
            }, this);
        },
        render: function() {
            return this;
        }
    });

    var App = Backbone.View.extend({
        el: $("body"),
        initialize: function() {
            this.container = $('#all-entries #entries-tables');
            this.listenTo(this.collection, "change", this.render);
            this.groups = this.collection.groupBy(function(entry) {
                return entry.get('project__name');
            });
            _.each(this.groups, function(group) {
                var table = new EntryTable({ collection: group });
                this.container.append(table.render().table);
            }, this)
        },
        events: {
            "click .btn[title='Verify All']": "verifyAll",
            "click .btn[title='Approve All']": "approveAll",
            "click .btn[title='Reject All']": "rejectAll",
            "change #filter-entries select": "filterEntries"
        },
        filterEntries: function(event) {
            /*
            entry_status = event.currentTarget.value;
            var coll;
            if (entry_status !== "") {
                this.filter = {'status': entry_status};
                coll = this.collection.where(this.filter);
            } else {
                coll = this.collection.toArray();
            }
            this.table.empty();
            _.each(coll, function(entry) {
                var view = new EntryRow({ model: entry });
                this.table.append(view.render().el);
            }, this)
            */
        },
        verifyAll: function(event) {
            event.preventDefault();
            this.collection.verify();
        },
        approveAll: function(event) {
            event.preventDefault();
            this.collection.approve();
        },
        rejectAll: function(event) {
            event.preventDefault();
            this.collection.reject();
        },
        render: function() {
            return this;
        }
    });

    app = new App({
        collection: new EntryCollection(JSON.parse(raw_entries))
    });
});
