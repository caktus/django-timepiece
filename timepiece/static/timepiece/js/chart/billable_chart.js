var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    hours = JSON.parse(script.getAttribute('data-hours')),
    wrapper,
    dataTable;

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

function drawChart() {
    if(hours.length > 1) {
        wrapper = new google.visualization.ChartWrapper({
            chartType: 'AreaChart',
            dataTable: google.visualization.arrayToDataTable(hours),
            options: {
                chartArea: {
                    width: '70%',
                    left: '5%'
                },
                pointSize: 6,
                isStacked: true
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
