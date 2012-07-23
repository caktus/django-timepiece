function Project(id, name) {
    this.id = id;
    this.name = name;
    this.row = 0;
}

function ProjectCollection() {
    this.projects = [];
}

ProjectCollection.prototype.add = function(project) {
    if(!this.get_by_id(project.id)) {
        this.projects.push(project);

        return true;
    }

    return false;
};

ProjectCollection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.projects.length; i++) {
        if(this.projects[i].id === id) {
            return this.projects[i];
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
        all_projects = data.all_projects,
        all_users = data.all_users,
        dataTable = [['']];
    

    for(var i = 0; i < all_projects.length; i++) {
        var p = all_projects[i],
            proj = new Project(p.id, p.name);

        this.all_projects.add(proj);
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

        var user = new User(ph.user, ph.user__first_name + ' ' + ph.user__last_name);
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

    // Load initial data
    getData($('h2[data-date]').data('date'));

    // Make sure the datepicker uses the correct format we expect
    $('.hasDatepicker').datepicker('option', 'dateFormat', 'yy-mm-dd' )
        .datepicker('setDate', $('h2[data-date]').data('date'));
});