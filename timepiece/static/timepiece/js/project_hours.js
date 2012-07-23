function Project(id, name) {
    this.id = id;
    this.name = name;
    this.row = 0;
}

function ProjectCollection() {
    this.collection = [];
}

ProjectCollection.prototype.add = function(project) {
    if(!this.get_by_id(project.id)) {
        this.collection.push(project);

        return true;
    }

    return false;
};

ProjectCollection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].id === id) {
            return this.collection[i];
        }
    }

    return null;
};

ProjectCollection.prototype.get_by_name = function(name) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].name === name) {
            return this.collection[i];
        }
    }

    return null;
};

var projects = new ProjectCollection();
var all_projects = new ProjectCollection();

function ProjectHours(id, hours, project) {
    this.id = id;
    this.hours = hours;
    this.project = project;
    this.user = null;
    this.row = 0;
    this.col = 0;
}

function ProjectHoursCollection() {
    this.collection = [];
}

ProjectHoursCollection.prototype.add = function(collection) {
    this.collection.push(collection);
};

ProjectHoursCollection.prototype.get_by_row_col = function(row, col) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].row === row && this.collection[i].col === col) {
            return this.collection[i];
        }
    }
};

ProjectHoursCollection.prototype.get_by_key = function(key, item) {
    var array = [];

    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i][key] == item) {
            array.push(this.collection[i]);
        }
    }

    return array;
};

var project_hours = new ProjectHoursCollection();

function User(id, name) {
    this.id = id;
    this.name = name;
    this.col = 0;
}

function UserCollection() {
    this.collection = [];
}

UserCollection.prototype.add = function(user) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].id === user.id) {
            return false;
        }
    }

    this.collection.push(user);
    return true;
};

UserCollection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].id === id) {
            return this.collection[i];
        }
    }
};

UserCollection.prototype.get_by_name = function(name) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].name === name) {
            return this.collection[i];
        }
    }
};

var users = new UserCollection();
var all_users = new UserCollection();

// Bootstrap's typeahead completion plugin expects strings, so we wrap the functions around the name
var model_prototype = {
    toLowerCase: function() {
        return this.name.toLowerCase();
    },

    indexOf: function(expr) {
        return this.name.indexOf(expr);
    },

    replace: function(regex, match) {
        return this.name.replace(regex, match);
    },

    toString: function() {
        return this.name;
    }
};

var collection_prototype = {
    index: function(item) {
        for(var i = 0; i < this.collection.length; i++) {
            if(this.collection[i].id === item.id) {
                return i;
            }
        }

        return -1;
    },

    remove: function(item) {
        var index = this.index(item);

        this.collection.splice(index, 1);
    }
};


$.extend(User.prototype, model_prototype);
$.extend(Project.prototype, model_prototype);

$.extend(UserCollection.prototype, collection_prototype);
$.extend(ProjectCollection.prototype, collection_prototype);
$.extend(ProjectHoursCollection.prototype, collection_prototype);

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
            new User(u.id, u.first_name + ' ' + u.last_name)
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
            dataTable[0].push(user.name);
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
                project, user;
            
            if(row === 0) {
                if(!users.get_by_name(after)) {
                    user = all_users.get_by_name(after);
                    
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