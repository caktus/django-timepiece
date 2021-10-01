var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    report = JSON.parse(script.getAttribute('data-report')),
    type = script.getAttribute('data-type');

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

function drawChart() {
    if(report.length > 1) {
        var chart_height = (report.length - 1) * 20,
            reverse = type === 'week' ? true : false,
            wrapper = new google.visualization.ChartWrapper({
            chartType: 'BarChart',
            dataTable: google.visualization.arrayToDataTable(report),
            options: {
                chartArea: {
                    bottom: 50,
                    height: chart_height,
                    left: '15%',
                    right: '10%',
                    top: 50,
                    width: '90%'
                },
                height: chart_height + 100,
                legend: {
                    alignment: 'center',
                    position: 'top'
                },
                reverseCategories: reverse
            },
            containerId: 'chart'
        });
        wrapper.draw();
    } else if (report.length === 1) {
        var container = $('#chart'),
            text = $('<p>No data to display.</p>');
        container.append(text);
    }
}
