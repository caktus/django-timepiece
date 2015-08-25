// function that resets and sets the available options in
// <select> for business department and business contacts, 
// based on the items associated with the selected business
function set_business_department_list_options($biz_list, $biz_dept_list) {
    $biz_dept_list.attr('disabled', true);
    var biz_id;
    if( $biz_list.val().trim() ) {
        biz_id = $biz_list.val();
    } else {
        biz_id = 0;
    }
    $.getJSON('/timepiece/business/' +  biz_id + '/departments/',
        function (data) {
            var first = $biz_dept_list.children()[0];
            $biz_dept_list.empty();
            $biz_dept_list.append(first);
            if (Object.keys(data).length) {
                $.each(data, function(key, biz_dept) {
                    $biz_dept_list.append('<option value="' + biz_dept.id + '">' + biz_dept.name + '</option>');
                });
            }
            $biz_dept_list.removeAttr('disabled');
        }
    );
}

function set_business_contact_list_options($biz_list, $biz_contact_list) {
    $biz_contact_list.attr('disabled', true);
    var biz_id;
    if( $biz_list.val().trim() ) {
        biz_id = $biz_list.val();
    } else {
        biz_id = 0;
    }
    $.getJSON('/timepiece/business/' +  biz_id + '/contacts/',
        function (data) {
            var first = $biz_contact_list.children()[0];
            $biz_contact_list.empty();
            $biz_contact_list.append(first);
            if (Object.keys(data).length) {
                $.each(data, function(key, biz_dept) {
                    $biz_contact_list.append('<option value="' + biz_dept.id + '">' + biz_dept.name + '</option>');
                });
            }
            $biz_contact_list.removeAttr('disabled');
        }
    );
}
