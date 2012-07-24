var projects = new ProjectCollection();
var all_projects = new ProjectCollection();

var users = new UserCollection();
var all_users = new UserCollection();

var project_hours = new ProjectHoursCollection();

function processData(data) {
    var projects = data.projects,
        project_hours = data.project_hours,
        all_projects = data.all_projects,
        all_users = data.all_users,
        dataTable = [['']];
    

    for(var i = 0; i < all_projects.length; i++) {
        var p = all_projects[i];

        this.all_projects.add(new Project(p.id, p.name));
    }

    for(i = 0; i < all_users.length; i++) {
        var u = all_users[i];

        this.all_users.add(
            new User(u.id, u.first_name + ' ' + u.last_name, u.first_name)
        );
    }

    for(i = 0; i < project_hours.length; i++) {
        var ph = project_hours[i],
            project = this.all_projects.get_by_id(ph.project);
        
        project.row = project.row || dataTable.length;

        var added = this.projects.add(project);

        if(added) {
            dataTable.push([project.name]);
        }

        var hours = new ProjectHours(ph.id, ph.hours, project);
        hours.row = project.row;

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

    $('.dataTable').handsontable('loadData', dataTable);
}

function getData(week_start) {
    if(!week_start) {
        var d = new Date();
        week_start = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
    }

    $.getJSON('/timepiece/ajax/hours/', { week_start: week_start }, function(data, status, xhr) {
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
        rows: 16,
        cols: 20,

        rowHeaders: true,
        colHeaders: true,

        minSpareRows: 1,
        minSpareCols: 1,

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
                    return (row > 0 && col > 0 && data()[row][col] !== '');
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
                    user = all_users.get_by_display_name(after);
                    
                    user.col = col;
                    users.add(user);
                } else {
                    $('.alert').show().html('User already listed').alert();

                    return false;
                }
            } else if(col === 0) {
                if(!projects.get_by_name(after)) {
                    // Adding project
                    project = all_projects.get_by_name(after);

                    project.row = row;
                    projects.add(project);
                } else {
                    $('.alert').show().html('Project already listed').alert();

                    return false;
                }
            } else if(row >= 1 && col >= 1) {
                var time = parseInt(after, 10);
                hours = project_hours.get_by_row_col(row, col);

                if(time && hours) {
                    $.post('/timepiece/ajax/hours/', {
                        'project': hours.project.id,
                        'user': hours.user.id,
                        'hours': time,
                        'week_start': $('h2[data-date]').data('date')
                    }, function(data, status, xhr) {
                        hours.hours = time;
                        $('.dataTable').handsontable('setDataAtCell', row, col, time);
                    }, function(xhr, status, error) {
                        $('.dataTable').handsontable('setDataAtCell', row, col, before);
                        $('.alert').show().html('Could not save the project hours. Please notify an administrator.').alert();
                    });
                } else if(time && !hours) {
                    project = projects.get_by_row(row);
                    user = users.get_by_col(col);

                    if(project && user && before === '') {
                        $.post('/timepiece/ajax/hours/', {
                            'user': user.id,
                            'project': project.id,
                            'hours': time,
                            'week_start': $('h2[data-date]').data('date')
                        }, function(data, status, xhr) {
                            hours = new ProjectHours(parseInt(data, 10), project, time);
                            hours.user = user;
                            project_hours.add(hours);
                        }, function(xhr, status, error) {
                            $('.dataTable').handsontable('setDataAtCell', row, col, '');
                            $('.alert').show().html('Could not save the project hours. Please notify an administrator.').alert();
                        });
                    } else {
                        $('.alert').show().html('Project hours must be associated with a project and user').alert();

                        return false;
                    }
                } else {
                    $('.alert').show().html('Project hours must be integers').alert();

                    return false;
                }
            } else {
                return;
            }
        },

        onChange: function(changes) {
            if(changes.length > 1) { return; }

            var row = changes[0][0],
                col = changes[0][1],
                before = changes[0][2],
                after = changes[0][3],
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
                hours = project_hours.get_by_row_col(row, col);

                if(hours && after === '') {
                    $.del('/timepiece/ajax/hours/' + hours.id + '/', function(data, status, xhr) {
                        project_hours.remove(hours);
                    }, function(xhr, status, error) {
                        $('.dataTable').handsontable('setDataAtCell', row, col, before);
                        $('.alert').show().html('Could not delete the project hours. Please notify an administrator.').alert();
                    });
                }
            } else {
                return;
            }
        }
    });

    // Load initial data
    getData($('h2[data-date]').data('date'));

    // Make sure the datepicker uses the correct format we expect
    $('.hasDatepicker').datepicker('option', 'dateFormat', 'yy-mm-dd' )
        .datepicker('setDate', $('h2[data-date]').data('date'));
});