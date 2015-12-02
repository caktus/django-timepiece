var projects = new ProjectCollection();
var all_projects = new ProjectCollection();

var users = new UserCollection();
var all_users = new UserCollection();

var project_hours = new ProjectHoursCollection();

function showError(msg) {
    var html = '<div class="alert alert-error">' + msg +
        '<a class="close" data-dismiss="alert" href="#">&times;</a></div>';

    $('#alerts').append(html);
    $('.alert').alert();
}

function processData(data) {
    var projects = data.projects,
        project_hours = data.project_hours,
        all_projects = data.all_projects,
        all_users = data.all_users,
        dataTable = [['']];

    if(typeof ajax_url === 'undefined') {
        ajax_url = data.ajax_url;
    }

    // Store all projects for autocomplete
    for(var i = 0; i < all_projects.length; i++) {
        var p = all_projects[i];

        this.all_projects.add(new Project(p.id, p.name));
    }

    // Store all users for autocomplete
    for(i = 0; i < all_users.length; i++) {
        var u = all_users[i],
            name = u.first_name + ' ' + u.last_name,
            display_name = u.first_name + ' ' + u.last_name[0] + '.';

        this.all_users.add(new User(u.id, name, display_name));
    }

    // Process all project hours to add to the table
    for(i = 0; i < project_hours.length; i++) {
        var ph = project_hours[i],
            project = this.all_projects.get_by_id(ph.project);

        project.row = project.row || dataTable.length;

        // Add project to table if it doesnt already exist
        if(this.projects.add(project)) {
            dataTable.push([project.name]);
        }

        var hours = new ProjectHours(ph.id, ph.hours, project, ph.published);
        hours.row = project.row;

        // Get from global users and add to datatable and adjust column
        // if the user isnt already in the table
        var user = this.all_users.get_by_id(ph.user);
        if(users.add(user)) {
            dataTable[0].push(user.display_name);
            user.col = dataTable[0].length - 1;
        } else {
            user = users.get_by_id(user.id);
        }

        hours.user = user;
        hours.col = user.col;

        if(!dataTable[hours.row]) {
            dataTable[hours.row] = [];
        }

        dataTable[hours.row][hours.col] = hours.hours;


        this.project_hours.add(hours);
    }

    // Populate the totals row after weve gone through all the data
    var totals = ['Totals'], j;

    for(i = 1; i < dataTable.length; i++) {
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
}

// Helper for updating totals after any change
function updateTotals(col, data) {
    var dataTable = $('.dataTable').handsontable('getData'),
        row = dataTable.length - 2,
        totals = dataTable[row];

    if(data !== '') {
        var current = parseInt(totals[col], 10);

        if(current) {
            current += data;
        } else {
            current = data;
        }

        $('.dataTable').handsontable('setDataAtCell', row, col, current);
    }
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

        fillHandle: false,

        minSpareRows: 1,
        minSpareCols: 1,

        minWidth: $('div#content').width() - 20, // -20 is to account for padding

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
                    var ph = project_hours.get_by_row_col(row, col);

                    if(ph && ph.published) {
                        return (row > 0 && col > 0 && data()[row][col] !== '');
                    }

                    return false;
                },
                style: {
                    color: 'white',
                    backgroundColor: 'green'
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
                    return (row === 0 && col !== 0);
                },
                source: function() {
                    return all_users.collection;
                }
            }
        ],

        onBeforeChange: function(changes) {
            if(changes.length > 4) { return; }

            var row = changes[0],
                col = changes[1],
                before = changes[2],
                after = changes[3],
                project, user, hours;

            if(row === 0) {
                if(!users.get_by_display_name(after)) {
                    // Adding a user
                    user = all_users.get_by_display_name(after);

                    user.col = col;
                    users.add(user);
                } else {
                    showError('User already listed');
                    return false;
                }
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
            } else if(row >= 1 && col >= 1) {
                var time = parseInt(after, 10);
                hours = project_hours.get_by_row_col(row, col);

                if(time && hours && time > 0) {
                    // If we have times and hours in the row/col, then update the current hours
                    $.post(ajax_url, {
                        'project': hours.project.id,
                        'user': hours.user.id,
                        'hours': time,
                        'week_start': $('h2[data-date]').data('date')
                    }, function(data, status, xhr) {
                        var diff = time - hours.hours;
                        updateTotals(col, diff);

                        hours.hours = time;
                        hours.published = false;
                        $('.dataTable').handsontable('setDataAtCell', row, col, time);
                    }, function(xhr, status, error) {
                        $('.dataTable').handsontable('setDataAtCell', row, col, before);
                        showError('Could not save the project hours. Please notify an administrator.');
                    });
                } else if(time && !hours && time > 0) {
                    // If the user entered a valid time, but the hours do not exist
                    // in a row/col, create them
                    project = projects.get_by_row(row);
                    user = users.get_by_col(col);

                    if(project && user && before === '') {
                        $.post(ajax_url, {
                            'user': user.id,
                            'project': project.id,
                            'hours': time,
                            'week_start': $('h2[data-date]').data('date')
                        }, function(data, status, xhr) {
                            hours = new ProjectHours(parseInt(data, 10), time, project, false);
                            hours.user = user;
                            hours.row = project.row;
                            hours.col = user.col;
                            project_hours.add(hours);
                            updateTotals(col, time);
                        }, function(xhr, status, error) {
                            $('.dataTable').handsontable('setDataAtCell', row, col, '');
                            showError('Could not save the project hours. Please notify an administrator.');
                        });
                    } else {
                        showError('Project hours must be associated with a project and user');
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

                        hours = project_hours.get_by_key('user', user);

                        for(i = 0; i < hours.length; i++) {
                            project_hours.remove(hours[i]);
                        }

                        $('.dataTable').handsontable('alter', 'remove_col', user.col);
                    }
                } else if(col === 0) {
                    project = projects.get_by_name(before);

                    if(project && after === '') {
                        projects.remove(project);

                        hours = project_hours.get_by_key('project', project);

                        for(i = 0; i < hours.length; i++) {
                            project_hours.remove(hours[i]);
                        }

                        $('.dataTable').handsontable('alter', 'remove_row', project.row);
                    }
                } else if(row >= 1 && col >= 1) {
                    function deleteHours() {
                        $.del(ajax_url + hours.id + '/', function(data, status, xhr) {
                            updateTotals(col, -hours.hours);

                            project_hours.remove(hours);
                            $('.dataTable').handsontable('setDataAtCell', row, col, '');
                        }, function(xhr, status, error) {
                            $('.dataTable').handsontable('setDataAtCell', row, col, before);
                            showError('Could not delete the project hours. Please notify an administrator.');
                        });
                    }

                    hours = project_hours.get_by_row_col(row, col);

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

    // Make sure they really want to copy project hours
    $('#copy').click(function(e) {
        var copy = confirm('This will overwrite a user\'s project hours if they exist. Are you sure you want to do this?');

        if(copy) {
            return true;
        }

        return false;
    });
});
