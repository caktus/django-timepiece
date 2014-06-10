function Model(id) {
    this.id = id;
}

Model.prototype.toLowerCase = function() {
    return this.name.toLowerCase();
};

Model.prototype.indexOf = function(expr) {
    return this.name.indexOf(expr);
};

Model.prototype.replace = function(regex, match) {
    return this.name.replace(regex, match);
};

Model.prototype.toString = function() {
    if(this.display_name) {
        return this.display_name;
    }

    return this.name;
};

function Project(id, name) {
    Model.call(this, id);

    this.name = name;
    this.row = 0;
}

Project.prototype = new Model();
Project.prototype.constructor = Project;

function Activity(id, name, code) {
    Model.call(this, id);

    this.name = name;
    this.code = code;
    this.row = 0;
}

Activity.prototype = new Model();
Activity.prototype.constructor = Activity;

function Location(id, name) {
    Model.call(this, id);

    this.name = name;
    this.row = 0;
}

Location.prototype = new Model();
Location.prototype.constructor = Location;

function User(id, name, display_name) {
    Model.call(this, id);

    this.name = name;
    this.display_name = display_name;
    this.col = 0;
}

User.prototype = new Model();
User.prototype.constructor = User;

function PeriodDate(date, display, weekday, col) {
    Model.call(this, date);

    this.date = date;
    this.display_name = display;
    this.weekday = weekday;
    this.col = col;
}

PeriodDate.prototype = new Model();
PeriodDate.prototype.constructor = PeriodDate;

function ChargedHours(id, project, user, start_time, end_time, activity, location) {
    Model.call(this, id);
    
    this.project = project;
    this.user = user;
    this.start_time = new Date(start_time);
    this.end_time = new Date(end_time);
    this.activity = activity;
    this.location =location;
    this.duration = 0;
    if (this.start_time && this.end_time) {
        // get duration in hours from timestamps
        this.duration = (this.end_time - this.start_time) / 3600000;
        // round to nearest quarter hour
        this.duration = Math.round(this.duration*4)/4;
    }
    this.row = 0;
    this.col = 0;
}

ChargedHours.prototype = new Model();
ChargedHours.prototype.constructor = ChargedHours;

function Collection() {
    this.collection = [];
}

Collection.prototype.add = function(item) {
    if(!this.get_by_id(item.id)) {
        this.collection.push(item);

        return true;
    }

    return false;
};

Collection.prototype.get_by_id = function(id) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].id === id) {
            return this.collection[i];
        }
    }

    return null;
};

Collection.prototype.get_by_name = function(name) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].name === name) {
            return this.collection[i];
        }
    }

    return null;
};

Collection.prototype.get_by_display_name = function(name) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].display_name === name) {
            return this.collection[i];
        }
    }

    return null;
};

Collection.prototype.get_by_key = function(key, item) {
    var array = [];

    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i][key] == item) {
            array.push(this.collection[i]);
        }
    }

    return array;
};

Collection.prototype.index = function(item) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].id === item.id) {
            return i;
        }
    }

    return -1;
};

Collection.prototype.remove = function(item) {
    var index = this.index(item);

    this.collection.splice(index, 1);
};

function ProjectCollection() {
    Collection.call(this);
}

ProjectCollection.prototype = new Collection();
ProjectCollection.prototype.constructor = ProjectCollection;

ProjectCollection.prototype.get_by_row = function(row) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].row === row) {
            return this.collection[i];
        }
    }

    return null;
};

function ActivityCollection() {
    Collection.call(this);
}

ActivityCollection.prototype = new Collection();
ActivityCollection.prototype.constructor = ActivityCollection;

ActivityCollection.prototype.get_by_row = function(row) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].row === row) {
            return this.collection[i];
        }
    }

    return null;
};

function LocationCollection() {
    Collection.call(this);
}

LocationCollection.prototype = new Collection();
LocationCollection.prototype.constructor = LocationCollection;

LocationCollection.prototype.get_by_row = function(row) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].row === row) {
            return this.collection[i];
        }
    }

    return null;
};

function UserCollection() {
    Collection.call(this);
}

UserCollection.prototype = new Collection();
UserCollection.prototype.constructor = UserCollection;

UserCollection.prototype.get_by_col = function(col) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].col === col) {
            return this.collection[i];
        }
    }

    return null;
};

function PeriodDatesCollection() {
    Collection.call(this);
}

PeriodDatesCollection.prototype = new Collection();
PeriodDatesCollection.prototype.constructor = PeriodDatesCollection;

PeriodDatesCollection.prototype.get_by_col = function(col) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].col === col) {
            return this.collection[i];
        }
    }

    return null;
};



function ChargedHoursCollection() {
    Collection.call(this);
}

ChargedHoursCollection.prototype = new Collection();
ChargedHoursCollection.prototype.constructor = ChargedHoursCollection;

ChargedHoursCollection.prototype.get_by_row_col = function(row, col) {
    for(var i = 0; i < this.collection.length; i++) {
        if(this.collection[i].row === row && this.collection[i].col === col) {
            return this.collection[i];
        }
    }

    return null;
};

// For testing in node
if(typeof module !== 'undefined') {
    module.exports = {
        'Model': Model,
        'Project': Project,
        'User': User,
        'Location': Location,
        'Activity': Activity,
        'ChargedHours': ChargedHours,
        'Collection': Collection,
        'ProjectCollection': ProjectCollection,
        'UserCollection': UserCollection,
        'ActivityCollection': ActivityCollection,
        'LocationCollection': LocationCollection,
        'ChargedHoursCollection': ChargedHoursCollection
    };
}
