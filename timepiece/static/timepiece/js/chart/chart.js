var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var billable = JSON.parse(script.getAttribute('data-billable')),
    nonbillable = JSON.parse(script.getAttribute('data-nonbillable'));

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper,
    data = [
        ['Type', 'Billable', 'Non-billable'],
        ['Hours', billable.total, nonbillable.total]
    ];

function drawChart() {
    wrapper = new google.visualization.ChartWrapper({
        chartType: 'ColumnChart',
        dataTable: google.visualization.arrayToDataTable(data),
        options: {
            chartArea: {
                width: '70%',
                left: '5%'
            }
        },
        containerId: 'chart'
    });

    wrapper.draw();
}

$(function() {
    $('.people input[type="checkbox"]').click(function() {
        if($(this).attr('checked') === 'checked') {
            data[1][1] += billable[$(this).attr('id')];
            data[1][2] += nonbillable[$(this).attr('id')];
        } else {
            data[1][1] -= billable[$(this).attr('id')];
            data[1][2] -= nonbillable[$(this).attr('id')];
        }

        wrapper.setDataTable(google.visualization.arrayToDataTable(data));
        wrapper.draw();
    });
});