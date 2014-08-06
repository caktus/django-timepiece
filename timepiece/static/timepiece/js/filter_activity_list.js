// function that resets and sets the available options in
// <select> for activities, based on the activities that
// can be charged for that project
function set_activity_list_options($proj_list, $act_list) {
    $act_list.attr('disabled', true);
    var project_id;
    if( $proj_list.val().trim() ) {
        project_id = $proj_list.val();
    } else {
        project_id = 0;
    }
    $.getJSON('/timepiece/project/' +  project_id + '/activities/',
        function (data) {
            if (Object.keys(data).length) {
                var first = $act_list.children()[0];
                $act_list.empty();
                $act_list.append(first);
                $.each(data, function(key, activity) {
                    $act_list.append('<option value="' + activity.id + '">' + activity.name + '</option>');
                });
                $act_list.removeAttr('disabled');
            }
        }
    );
}
