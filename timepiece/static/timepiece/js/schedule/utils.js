var GET_ERROR_MSG = 'An error occurred while loading the schedule data from ' +
                    'the server. If refreshing the page does not help, ' +
                    'please contact an administrator.';

var POST_ERROR_MSG = 'An error occurred while making the requested changes ' +
                     'on the server. If refreshing the page does not help, ' +
                     'please contact an administrator.';

var DEL_ERROR_MSG = 'An error occurred while making the requested changes ' +
                    'on the server. If refreshing the page does not help, ' +
                    'please contact an administrator.';

function addMessage(msg, type) {
    var html = '<div class="alert alert-' + type + '">' +
                   msg +
                   '<a class="close" data-dismiss="alert" href="#">&times;</a>' +
               '</div>';
    $('#alerts').append(html);
    $('.alert').alert();
}

function showError(msg) {
    addMessage(msg, 'error');
}

function ajax(data, success, error, type) {
    $.ajax({
        type: type,
        dataType: 'json',
        url: ajax_url,
        data: data,
        success: success,
        error: error,
    });
}

// Retrieve schedule data from server.
function get(data, success, error) {
    ajax(data, success, error, 'GET');
}

// Edit assignment on server.
function post(data, success, error) {
    ajax(data, success, error, 'POST');
};

// Delete assignment on server.
function del(data, success, error) {
    ajax(data, success, error, 'DELETE');
};

function getToday() {
    var d = new Date();
    return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
}

function id_list_from_collection(collection) {
    var id_list = [], i;
    for (i = 0; i < collection.length; i++) {
        id_list.push(collection[i].id);
    }
    return id_list;
}

function reassign_user_data(collection, new_user_id) {
    var data = [];
    for (i = 0; i < collection.length; i++) {
        var map = {
            user: new_user_id,
            project: collection[i].project.id,
            hours: collection[i].hours
        };
        data.push(map);
    }
    return data;
}

function reassign_project_data(collection, new_project_id) {
    var data = [];
    for (i = 0; i < collection.length; i++) {
        var map = {
            user: collection[i].user.id,
            project: new_project_id,
            hours: collection[i].hours
        };
        data.push(map);
    }
    return data;
}

function get_assignment_data(id, user, project, hours) {
    var map = {
        id: id,
        user: user.id,
        project: project.id,
        hours: hours
    };
    return [map];
}
