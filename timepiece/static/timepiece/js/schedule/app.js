/*
 * Future TODO:
 *
 * Allow editing of multiple cells (as through copy & paste).
 * Better way of handling users in the case of duplicate names/display names.
 * Check that server errors return as expected.
 * When things go wrong & could be out of sync, force refresh or hide data table.
 * Rendering issues when chart runs off page.
 * Update totals row
 */

var schedule_id = '#schedule';

// Used for autocomplete.
var all_projects = new ProjectCollection(),
    all_users = new UserCollection();

// The users & projects currently displayed.
var projects = new ProjectCollection(),
    users = new UserCollection();

var assignments = new ProjectHoursCollection();

// Parses schedule data, adjusts local variables, and replaces handsontable
// data with the new schedule.
function processData(data) {
    var all_projects = data.all_projects,
        all_users = data.all_users,
        assignments = data.assignments,
        dataTable = [['']];  // Include empty row for users' names.

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

    // Add each assignment to the table.
    for(i = 0; i < assignments.length; i++) {
        var project = this.all_projects.get_by_id(assignments[i].project__id),
            user = this.all_users.get_by_id(assignments[i].user__id);

        // If the project isn't already in the table, add another row.
        if (this.projects.add(project)) {
            dataTable.push([project.name]);
            project.row = dataTable.length - 1;
        } else {
            project = this.projects.get_by_id(project.id);  // To get row info.
        }

        // If the user isn't already in the table, add another column.
        if (this.users.add(user)) {
            dataTable[0].push(user.display_name);
            user.col = dataTable[0].length - 1;
        } else {
            user = this.users.get_by_id(user.id);  // To get col info.
        }

        // Create a new ProjectHours object.
        var assignment = new ProjectHours(assignments[i].id,
                assignments[i].hours, project, assignments[i].published);
        assignment.user = user;
        assignment.col = user.col;
        assignment.row = project.row;
        this.assignments.add(assignment);

        // Add the assignment to the table.
        if (!dataTable[assignment.row]) {
            dataTable[assignment.row] = [];
        }
        dataTable[assignment.row][assignment.col] = assignment.hours;
    }

    // Finally, populate the totals row.
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
    dataTable.push([], [], totals);  // Include 2 blank rows before totals.

    $(schedule_id).handsontable('loadData', dataTable);
}

// Helper for updating totals after any change
function updateTotals(col, data) {
    var dataTable = $(schedule_id).handsontable('getData'),
        row = dataTable.length - 2,  // Next-to-last row.
        totals = dataTable[row];

    if(data !== '') {
        var current = parseInt(totals[col], 10);

        if(current) {
            current += data;
        } else {
            current = data;
        }

        $(schedule_id).handsontable('setDataAtCell', row, col, current);
    }
}

// Load the schedule for the week containing the given day.
function getData(week_start) {
    if (!week_start) {
        week_start = getToday();
    }

    // Get JSON data from server.
    var data = {week_start: week_start};
    get(data,
        function (data, status, xhr) {
            processData(data);
        },
        function (xhr, status, error) {
            showError(GET_ERROR_MSG);
        }
    );
}

function unpublishedRenderer (instance, td, row, col, prop, value, cellProperties) {
    Handsontable.TextCell.renderer.apply(this, arguments);
    $(td).removeClass('published');
    $(td).addClass('unpublished');
}

function publishedRenderer (instance, td, row, col, prop, value, cellProperties) {
    Handsontable.TextCell.renderer.apply(this, arguments);
    $(td).removeClass('unpublished');
    $(td).addClass('published');
}

function changeUser(row, col, before, after) {
    var old_user = all_users.get_by_display_name(before),
        new_user = all_users.get_by_display_name(after),
        existing_assignments = assignments.get_by_user(old_user);

    if (old_user) {  // Remove old assignments from server.
        if (existing_assignments.length > 0) {
            var id_list = JSON.stringify(id_list_from_collection(existing_assignments));
            del(id_list,
                function(data, status, xhr) {  // Remove local information.
                    users.remove(old_user);
                    assignments.remove_all(existing_assignments);
                    if (!new_user) {
                        $(schedule_id).handsontable('alter', 'remove_col', col);
                    }
                },
                function(xhr, status, error) {
                    showError(DEL_ERROR_MSG);
                    return false;
                }
            );
        } else {
            users.remove(old_user);
            if (!new_user) {
                $(schedule_id).handsontable('alter', 'remove_col', col);
            }
        }
    }
    if (new_user) {  // Add new assignments to server.
        if (existing_assignments.length > 0) {
            var data = JSON.stringify(reassign_user_data(existing_assignments, new_user.id));
            post(data,
                 function(data, status, xhr) {  // Add local information.
                    new_user.col = col;
                    users.add(new_user);
                    for (var i = 0; i < existing_assignments.length; i++) {
                        var assignment = existing_assignments[i];
                        assignment.id = data[i];
                        assignment.user = new_user;
                        assignment.published = false;
                        assignments.add(assignment);
                    }
                    $(schedule_id).handsontable('render');  // To update formatting.
                },
                function(xhr, status, error) {
                    showError(POST_ERROR_MSG);
                    return false;
                }
            );
        } else {
            new_user.col = col;
            users.add(new_user);
        }
    }
}

function changeProject(row, col, before, after) {
    var old_project = all_projects.get_by_name(before),
        new_project = all_projects.get_by_name(after),
        existing_assignments = assignments.get_by_project(old_project);
    if (old_project) {  // Remove old assignments from server.
        if (existing_assignments.length > 0) {
            var id_list = JSON.stringify(id_list_from_collection(existing_assignments));
            del(id_list,
                function(data, status, xhr) {  // Remove local information.
                    projects.remove(old_project);
                    assignments.remove_all(existing_assignments);
                    if (!new_project) {
                        $(schedule_id).handsontable('alter', 'remove_row', row);
                    }
                },
                function(xhr, status, error) {
                    showError(DEL_ERROR_MSG);
                    return false;
                }
            );
        } else {
            projects.remove(old_project);  // Remove local information.
            if (!new_project) {
                $(schedule_id).handsontable('alter', 'remove_row', row);
            }
        }
    }
    if (new_project) {  // Add new assignments to server.
        if (existing_assignments.length > 0) {
            var data = JSON.stringify(reassign_project_data(existing_assignments, new_project.id));
            post(data,
                 function(data, status, xhr) {  // Add local information.
                     new_project.row = row;
                     projects.add(new_project);
                     for (var i = 0; i < existing_assignments.length; i++) {
                         var assignment = existing_assignments[i];
                         assignment.id = data[i];
                         assignment.published = false;
                         assignment.project = new_project;
                         assignments.add(assignment);
                     }
                     $(schedule_id).handsontable('render');  // To update formatting.
                 },
                 function(xhr, status, error) {
                     showError(POST_ERROR_MSG);
                     return false;
                 }
            );
        } else if (new_project) {  // Add local information.
            new_project.row = row;
            projects.add(new_project);
        }
    }
}

function changeAssignment(row, col, before, after) {
    var old_assignment = assignments.get_by_row_col(row, col);
    if (old_assignment && after === '') {  // Remove assignment from server.
        var del_data = JSON.stringify([old_assignment.id]);
        del(del_data,
            function(data, status, xhr) {  // Remove local information.
                assignments.remove(old_assignment);
                $(schedule_id).handsontable('render');  // To update formatting.
            },
            function(xhr, status, error) {
                showError(DEL_ERROR_MSG);
                return false;
            }
        );
    } else if (old_assignment) {  // Update existing assignment on server.
        var data = get_assignment_data(old_assignment.id, old_assignment.user,
                                       old_assignment.project, after);
        var post_data = JSON.stringify(data);
        post(post_data,
            function(data, status, xhr) {  // Update local information..
                old_assignment.hours = after;
                old_assignment.published = false;
                $(schedule_id).handsontable('render');  // To update formatting.
            },
            function(xhr, status, error) {
                showError(POST_ERROR_MSG);
                return false;
            }
        );
    } else if (after !== '') {  // Add new assignment to server.
        var user = users.get_by_col(col),
            project = projects.get_by_row(row),
            data = get_assignment_data(null, user, project, after),
            post_data = JSON.stringify(data);
        post(post_data,
            function(data, status, xhr) {  // Add local information.
                assignment = new ProjectHours(data[0], after, project, false);
                assignment.user = user;
                assignment.row = row;
                assignment.col = col;
                assignments.add(assignment);
                $(schedule_id).handsontable('render');  // To update formatting.
            },
            function(xhr, status, error) {
                showError(POST_ERROR_MSG);
                return false;
            }
        );
    }
}

$(function() {
    // First, add an empty handsontable.
    $(schedule_id).handsontable({
        fillHandle: false,
        minSpareCols: 1,
        multiSelect: false,
        startCols: 0,
        startRows: 0,
        stretchH: 'all',

        cells: function (row, col, prop) {
            if (row > 0 && col > 0) {
                var assignment = assignments.get_by_row_col(row, col);
                if (assignment && assignment.published) {
                    return {type: {renderer: publishedRenderer}};
                } else if (assignment) {
                    return {type: {renderer: unpublishedRenderer}};
                }
            }
        },

        autoComplete: [
            {  // Autocomplete project names on the first column.
                match: function(row, col, data) {
                    return (col === 0 && row !== 0);
                },
                source: function(row, col) {
                    return all_projects.collection;
                },
                strict: true
            },
            {  // Autocomplete user names on the first row.
                match: function(row, col, data) {
                    return (row === 0 && col !== 0);
                },
                source: function() {
                    return all_users.collection;
                },
                strict: true
            }
        ],

        // Validate the input. Returning false aborts all changes.
        onBeforeChange: function(changes) {
            if (changes.length !== 1) {
                showError('Only one cell may be edited at a time.');
                return false;
            }

            var row = changes[0][0],
                col = changes[0][1],
                before = changes[0][2],
                after = changes[0][3],
                msg;

            // Don't continue if no change was made.
            // TODO: compare float values, taking into account floating point errors.
            if (String(before) === String(after)) { return false; }

            // Don't allow any value in the first cell.
            else if (row === 0 && col === 0) { return false; }

            // Validate adding or changing a user.
            else if (row === 0 && (before === '' || after !== '')) {
                var user = all_users.get_by_display_name(after);
                if (!user) {
                    msg = 'There is no user with the name \'' + after + '\'.';
                } else if (users.index(user) > -1) {
                    msg = after + ' is already listed on the schedule.';
                } else {
                    changes[0][3] = user.display_name;  // Change value to display name.
                }
            }

            // Validate adding or changing a project.
            else if (col === 0 && (before === '' || after !== '')) {
                var project = all_projects.get_by_name(after);
                if (!project) {
                    msg = 'There is no project with the name \'' + after + '\'.';
                } else if (projects.index(project) > -1) {
                    msg = after + ' is already listed on the schedule.';
                }
            }

            // Validate adding or changing an assignment.
            else {
                // Standardize input by trimming whitespace.
                after = $.trim(after);
                changes[0][3] = after;

                if (after !== '') {
                    var assignment = parseFloat(after);
                    if (isNaN(assignment) || assignment < 0) {
                        msg = 'Assignments must be non-negative numbers.';
                    } else if (assignment === 0) {
                        changes[0][3] = '';  // Change 0 assignments to blank.
                    } else if (!users.get_by_col(col) || !projects.get_by_row(row)) {
                        changes[0][3] = before;
                        msg = 'Please create both a user and a project for that ' +
                              'row/col before creating an assignment.';
                    }
                }
            }

            if (msg) {
                showError(msg);
                return false;
            }
        },

        onChange: function(changes, source) {
            if (source === 'loadData') { return; }

            // This occurs when changes have been invalidated during onBeforeChange.
            if (changes.length === 0) { return; }

            var row = changes[0][0],
                col = changes[0][1],
                before = changes[0][2],
                after = changes[0][3];

            if (before === after) { return; }  // Pragma - validation prevents this.
            else if (row === 0 && col === 0) { return; }  // Pragma - validation prevents this.
            else if (row === 0) { return changeUser(row, col, before, after); }
            else if (col === 0) { return changeProject(row, col, before, after); }
            else { return changeAssignment(row, col, before, after); }

            // TODO: update totals row.
        }
    });

    // After creating the handsontable, load initial data from the server.
    getData(week_start);
});
