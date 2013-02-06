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
        error: error
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
