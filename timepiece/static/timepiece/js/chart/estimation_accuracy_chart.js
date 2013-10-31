var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    data = JSON.parse(script.getAttribute('data')),
    wrapper,
    dataTable;

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

function drawChart() {
    if(data.length > 1) {
	dataTable = google.visualization.arrayToDataTable(data);
	dataTable.setColumnProperty(2, 'role', 'tooltip');
        wrapper = new google.visualization.ChartWrapper({
            chartType: 'ScatterChart',
            dataTable: dataTable,
            options: {
		title: "Estimation Accuracy",
		hAxis: {title: 'Contracted Hours', minValue: 0, maxValue: 800},
		vAxis: {title: 'Worked Hours', minValue: 0, maxValue: 800},
                chartArea: {
                    width: '100%',
                    left: '5%'
                },
                pointSize: 6,
                isStacked: false 
            },
            containerId: 'chart'
        });
        wrapper.draw();
    }
}

$(function() {
    // Add "select all" and "select none" clickable links to form labels.

    $('a.select-all').click(function(e) {
        e.preventDefault();
        $(this).parent().parent()
            .next()
            .children()
            .each(function(i, e) {
                $(e).find('input').attr('checked', 'checked');
            });
        return false;
    });

    $('a.select-none').click(function(e) {
        e.preventDefault();
        $(this).parent().parent()
            .next()
            .children()
            .each(function(i, e) {
                $(e).find('input').removeAttr('checked');
            });
        return false;
    });
});
