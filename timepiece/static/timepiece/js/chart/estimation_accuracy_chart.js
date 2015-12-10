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
                vAxis: {title: 'Actual Hours', minValue: 0, maxValue: chart_max, textPosition : 'in'},
                hAxis: {title: 'Target Hours', minValue: 0, maxValue: chart_max, textPosition : 'in'},
                titlePosition: 'in',
                trendlines: {
                       0: {color: 'purple', opacity: 0.2, showR2: true, visibleInLegend: true}
                },
                chartArea: {
                    width: '100%',
                    height: '95%',
                    left: '5%',
                    top: '0',
                }
            },
            containerId: 'chart'
        });
        wrapper.draw();
    }
}
