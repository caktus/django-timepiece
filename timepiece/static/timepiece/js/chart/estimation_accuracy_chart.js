var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    data = JSON.parse(script.getAttribute('data')),
    chart_max = JSON.parse(script.getAttribute('chart_max')),
    wrapper,
    dataTable;
google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

function drawChart() {
    if(data.length > 1) {
        dataTable = google.visualization.arrayToDataTable(data);

        //Make column 3 the "tooltip" / mouse-over label.
        dataTable.setColumnProperty(2, 'role', 'tooltip');

        wrapper = new google.visualization.ChartWrapper({
            chartType: 'ScatterChart',
            dataTable: dataTable,
            options: {
                title: 'Estimation Accuracy',
                vAxis: {title: 'Actual Hours', minValue: 0, maxValue: chart_max},
                hAxis: {title: 'Target Hours', minValue: 0, maxValue: chart_max},
                trendlines: {
                       0: {color: 'purple', lineWidth: 8, opacity: 0.2}
                },
                chartArea: {
                    width: '100%',
                    left: '5%'
                }
            },
            containerId: 'chart'
        });
        wrapper.draw();
    }
}
