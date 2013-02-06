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

function User(id, name, display_name) {
    Model.call(this, id);

    this.name = name;
    this.display_name = display_name;
    this.col = 0;
}

User.prototype = new Model();
User.prototype.constructor = User;

function ProjectHours(id, hours, project, published) {
    Model.call(this, id);

    this.hours = hours;
    this.project = project;
    this.user = null;
    this.row = 0;
    this.col = 0;
    this.published = published;
}

ProjectHours.prototype = new Model();
ProjectHours.prototype.constructor = ProjectHours;

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

function ProjectHoursCollection() {
    Collection.call(this);
}

ProjectHoursCollection.prototype = new Collection();
ProjectHoursCollection.prototype.constructor = ProjectHoursCollection;

ProjectHoursCollection.prototype.get_by_row_col = function(row, col) {
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
        'ProjectHours': ProjectHours,
        'Collection': Collection,
        'ProjectCollection': ProjectCollection,
        'UserCollection': UserCollection,
        'ProjectHoursCollection': ProjectHoursCollection
    };
}
