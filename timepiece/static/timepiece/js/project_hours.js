function Project(id, name) {
    this.id = id;
    this.name = name;
    this.row = 0;
}

function ProjectCollection() {
    this.projects = [];
}

ProjectCollection.prototype.add = function(project) {
    if(this.projects.indexOf(project) < 0) {
        this.projects.push(project);
    } else {
        console.warn('Project already added');
    }
};

ProjectCollection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.projects.length; i++) {
        if(this.projects[i].id === id) {
            return this.projects[i];
        }
    }
};

var projects = new ProjectCollection();

function ProjectHours(id, hours, project) {
    this.id = id;
    this.hours = hours;
    this.project = project;
    this.user = null;
    this.row = 0;
    this.col = 0;
}

function ProjectHoursCollection() {
    this.project_hours = [];
}

ProjectHoursCollection.prototype.add = function(project_hours) {
    this.project_hours.push(project_hours);
};

ProjectHoursCollection.prototype.get_by_row_col = function(row, col) {
    for(var i = 0; i < this.project_hours.length; i++) {
        if(this.project_hours[i].row === row && this.project_hours[i].col === col) {
            return this.project_hours[i];
        }
    }
};

var project_hours = new ProjectHoursCollection();

function User(id, display_name) {
    this.id = id;
    this.display_name = display_name;
    this.col = 0;
}

function UserCollection() {
    this.users = [];
}

UserCollection.prototype.add = function(user) {
    for(var i = 0; i < this.users.length; i++) {
        if(this.users[i].id === user.id) {
            return false;
        }
    }

    this.users.push(user);
    return true;
};

UserCollection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.users.length; i++) {
        if(this.users[i].id === id) {
            return this.users[i];
        }
    }
};

var users = new UserCollection();

function processData(data) {
    var projects = data.projects,
        project_hours = data.project_hours,
        dataTable = [['']];
    

    for(var i = 0; i < projects.length; i++) {
        var p = projects[i],
            proj = new Project(p.id, p.name);

        proj.row = i + 1;

        this.projects.add(proj);

        dataTable.push([proj.name]);
    }

    for(i = 0; i < project_hours.length; i++) {
        var ph = project_hours[i],
            project = this.projects.get_by_id(ph.project);

        var hours = new ProjectHours(ph.id, ph.hours, project);
        hours.row = project.row;

        var user = new User(ph.user, ph.user__first_name);
        if(users.add(user)) {
            dataTable[0].push(user.display_name);
            user.col = dataTable[0].length - 1;
        } else {
            user = users.get_by_id(user.id);
        }

        hours.user = user;
        hours.col = user.col;
        dataTable[hours.row][hours.col] = hours.hours;


        this.project_hours.add(hours);
    }

    $('.dataTable').handsontable('loadData', dataTable);
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

        onBeforeChange: function(changes) {
            // todo
        },
        onChange: function(changes) {
            // todo
        }
    });

    var d = new Date();
    var week_of = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();

    // Load initial data
    $.getJSON('/timepiece/ajax/hours/', { week_of: week_of }, function(data, status, xhr) {
        processData(data);
    });
});