var projects = new ProjectCollection();
var all_projects = new ProjectCollection();

//var activities = new ActivityCollection();
var all_activities = new ActivityCollection();

//var locations = new LocationCollection();
var all_locations = new LocationCollection();

var users = new UserCollection();
var period_dates = new PeriodDatesCollection();

var charged_hours = new ChargedHoursCollection(); 

function showError(msg) {
    var html = '<div class="alert alert-error">' + msg +
        '<a class="close" data-dismiss="alert" href="#">&times;</a></div>';

    $('#alerts').append(html);
    $('.alert').alert();
}

function processData(data) {
    var projects = data.projects,
        charged_hours = data.charged_hours,
        all_projects = data.all_projects,
        all_activities = data.all_activities,
        all_locations = data.all_locations,
        period_dates = data.period_dates,
        dataTable = [['Project', 'Activity', 'Location']];

    if(typeof ajax_url === 'undefined') {
        ajax_url = data.ajax_url;
    }

    // Store all projects for autocomplete
    for(var i = 0; i < all_projects.length; i++) {
        var p = all_projects[i];

        this.all_projects.add(new Project(p.id, p.name));
    }

    // Store all activities for autocomplete
    for(var i = 0; i < all_activities.length; i++) {
        var a = all_activities[i];

        this.all_activities.add(new Activity(a.id, a.name));
    }

    // Store all locations for autocomplete
    for(var i = 0; i < all_locations.length; i++) {
        var l = all_locations[i];

        this.all_locations.add(new Location(l.id, l.name));
    }

    // Create mapping for dates and populate first row
    for(var i = 0; i < period_dates.length; i++) {
        var pd = period_dates[i];

        this.period_dates.add(new PeriodDate(pd.date, pd.display, pd.weekday, i+3));
        dataTable[0].push(pd.display);
    }

    // Process all charged hours to add to the table
    for(i = 0; i < charged_hours.length; i++) {
        var ch = charged_hours[i],
            project = this.all_projects.get_by_id(ch.project);

        project.row = project.row || dataTable.length;

        // Add project to table if it doesnt already exist
        if(this.projects.add(project)) {
            dataTable.push([project.name]);
        }
        
        var hours = new ChargedHours(ch.id, ch.project, ch.user, ch.start_time, ch.end_time, ch.activity, ch.location);
        hours.row = project.row;

        var date = this.period_dates.get_by_id(ch.start_time.slice(0,10));
        hours.date = date;
        hours.col = date.col;

        if(!dataTable[hours.row]) {
            dataTable[hours.row] = [];
        }

        if (dataTable[hours.row][hours.col]) {
            dataTable[hours.row][hours.col] += hours.duration;
        } else {
            dataTable[hours.row][hours.col] = hours.duration;
        }

        var activity = this.all_activities.get_by_id(ch.activity);
        dataTable[hours.row][1] = activity.name;
        var location = this.all_locations.get_by_id(ch.location);
        dataTable[hours.row][2] = location.name;

        this.charged_hours.add(hours);
    }

    // Populate the totals row after weve gone through all the data
    var totals = ['Totals', '', ''], j;

    for(i = 3; i < dataTable.length; i++) {
        var row = dataTable[i];

        for(j = 1; j < row.length; j++) {
            if(!totals[j]) {
                totals[j] = 0;
            }

            if(row[j]) {
                totals[j] += row[j];
            }
        }
    }
    dataTable.push([], [], totals);

    $('.dataTable').handsontable('loadData', dataTable);
    
    for (var c=3; c<dataTable[0].length; c++) {
        updateTotals(c);
    }
}

// Helper for updating totals after any change
// TODO: make more robust
function updateTotals(col) {
    var dataTable = $('.dataTable').handsontable('getData'),
        row = dataTable.length - 3,
        total = 0;

    for (var r=row; r>=1; r--){
        temp = parseFloat( dataTable[r][col] )
        if (!isNaN(temp)) {
            total += temp;
        }
    }

    $('.dataTable').handsontable('setDataAtCell', row+1, col, total);
}

// Entry point to load all data into the table
function getData(week_start) {
    if(!week_start) {
        var d = new Date();
        week_start = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
    }

    $.getJSON(ajax_url, { week_start: week_start }, function(data, status, xhr) {
        processData(data);
    });
}

function ajax(url, data, success, error, type) {
    $.ajax({
        type: type,
        url: url,
        data: data,
        success: success,
        error: error
    });
}

// Override post to take an error callback
$.post = function(url, data, success, error) {
    ajax(url, data, success, error, 'POST');
};

// Add wrappers for put and delete
$.put = function(url, data, success, error) {
    ajax(url, data, success, error, 'PUT');
};

$.del = function(url, success, error) {
    ajax(url, { }, success, error, 'DELETE');
};

$(function() {
    var table = $('.dataTable').handsontable({
        rows: 3,
        cols: 4,

        fillHandle: false,

        minSpareRows: 1,
        minSpareCols: 0,

        //minWidth: $('div#content').width() - 60, // -20 is to account for padding

        enterBeginsEditing: true,

        legend: [
            {   // Match the first row and bold it
                match: function(row, col, data) {
                    return (row === 0);
                },
                style: {
                    fontWeight: 'bold'
                }
            },
            {   // Match the cells with content
                match: function(row, col, data) {
                    var ph = charged_hours.get_by_row_col(row, col);

                    if(ph) {
                        return (row > 0 && col > 0 && data()[row][col] !== '');
                    }

                    return false;
                },
                style: {
                    color: 'white',
                    backgroundColor: '#236b8e'
                }
            },
            {   // Match the cells with content
                match: function(row, col, data) {
                    return 0 <= col && col <= 2;
                },
                style: {
                    color: 'black',
                    backgroundColor: 'white'
                }
            }
        ],

        autoComplete: [
            {
                match: function(row, col, data) {
                    return (col === 0);
                },
                source: function() {
                    return all_projects.collection;
                }
            },
            {
                match: function(row, col, data) {
                    return (col === 1);
                },
                source: function() {
                    return all_activities.collection;
                }
            },
            {
                match: function(row, col, data) {
                    return (col === 2);
                },
                source: function() {
                    return all_locations.collection;
                }
            },
        ],

        onBeforeChange: function(changes) {
            if(changes.length > 4) { return; }

            var row = changes[0],
                col = changes[1],
                before = changes[2],
                after = changes[3],
                project, user, duration, date;

            if(row === 0) {
                return;

            } else if(col === 0) {
                if(!projects.get_by_name(after)) {
                    // Adding project
                    project = all_projects.get_by_name(after);

                    project.row = row;
                    projects.add(project);

                    // Keep rows in between projects and totals
                    $('.dataTable').handsontable('alter', 'insert_row', row + 1);
                } else {
                    showError('Project already listed');
                    return false;
                }

            } else if(row >= 1 && col >= 3) {
                var time = parseFloat(after);
                time = Math.round(time*4)/4;
                $('.dataTable').handsontable('setDataAtCell', row, col, time);
                hours = charged_hours.get_by_row_col(row, col);
                
                if(time && hours && time > 0) {
                    // If we have times and hours in the row/col, then update the current hours
                    $.post(ajax_url, {
                        'entry_id': hours.id,
                        'project': hours.project,
                        'activity': hours.activity,
                        'location': hours.location,
                        'user': hours.user,
                        'duration': time,
                        'period_start': $('h2[data-date]').data('date')
                    }, function(data, status, xhr) {
                        hours.hours = time;
                        $('.dataTable').handsontable('setDataAtCell', row, col, time);
                        updateTotals(col);
                    }, function(xhr, status, error) {
                        $('.dataTable').handsontable('setDataAtCell', row, col, before);
                        showError('Could not save the project hours. Please notify an administrator.');
                    });
                } else if(time && !hours && time > 0) {
                    // If the user entered a valid time, but the hours do not exist
                    // in a row/col, create them
                    project = projects.get_by_row(row);
                    date = period_dates.get_by_col(col);

                    if(project && date && before === '') {
                        $.post(ajax_url, {
                            'project': project.id,
                            'duration': time,
                            'date': date.id,
                            'period_start': $('h2[data-date]').data('date')
                        }, function(data, status, xhr) {
                            hours = new ChargedHours(parseInt(data['id']), project, user, data['start_time'], data['end_time']);
                            hours.row = project.row;
                            hours.col = user.col;
                            charged_hours.add(hours);

                            updateTotals(col);
                        }, function(xhr, status, error) {
                            $('.dataTable').handsontable('setDataAtCell', row, col, '');
                            showError('Could not save the project hours. Please notify an administrator.');
                        });
                    } else {
                        showError('Project hours must be associated with a project and date');
                        return false;
                    }
                } else {
                    if(after !== '' && !hours || time <= 0) {
                        showError('Project hours must be integers greater than zero');
                        return false;
                    }
                }
            } else {
                return;
            }
        },

        onChange: function(changes, source) {
            if(source === 'loadData') { return; }

            for(j = 0; j < changes.length; j++) {
                var row = changes[j][0],
                    col = changes[j][1],
                    before = changes[j][2],
                    after = changes[j][3],
                    project, user, hours, i;

                if(row === 0) {
                    user = users.get_by_name(before);

                    if(user && after === '') {
                        users.remove(user);

                        hours = charged_hours.get_by_key('user', user);

                        for(i = 0; i < hours.length; i++) {
                            charged_hours.remove(hours[i]);
                        }

                        $('.dataTable').handsontable('alter', 'remove_col', user.col);
                    }
                } else if(col === 0) {
                    project = projects.get_by_name(before);

                    if(project && after === '') {
                        projects.remove(project);

                        hours = charged_hours.get_by_key('project', project);

                        for(i = 0; i < hours.length; i++) {
                            charged_hours.remove(hours[i]);
                        }

                        $('.dataTable').handsontable('alter', 'remove_row', project.row);
                    }
                } else if(row >= 1 && col >= 1) {
                    function deleteHours() {
                        $.del(ajax_url + hours.id + '/', function(data, status, xhr) {
                            updateTotals(col);

                            charged_hours.remove(hours);
                            $('.dataTable').handsontable('setDataAtCell', row, col, '');
                        }, function(xhr, status, error) {
                            $('.dataTable').handsontable('setDataAtCell', row, col, before);
                            showError('Could not delete the project hours. Please notify an administrator.');
                        });
                    }

                    hours = charged_hours.get_by_row_col(row, col);

                    if(hours && after === '') {
                        // If the hours have been removed from the table, delete from
                        // the database
                        deleteHours();
                    } else if(hours && after == '0') {
                        // If the hours have been zeroed out in the table, delete from
                        // the database
                        deleteHours();
                    }
                } else {
                    return;
                }
            }
        }
    });

    // Load initial data
    getData($('h2[data-date]').data('date'));

    // Make sure the datepicker uses the correct format we expect
    $('.hasDatepicker').datepicker('setDate', $('h2[data-date]').data('date'));

    // // Make sure they really want to copy project hours
    // $('#copy').click(function(e) {
    //     var copy = confirm('This will overwrite a user\'s project hours if they exist. Are you sure you want to do this?');

    //     if(copy) {
    //         return true;
    //     }

    //     return false;
    // });
});
