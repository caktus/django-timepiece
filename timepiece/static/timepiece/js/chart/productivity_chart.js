var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var labels = JSON.parse(script.getAttribute('data-labels')),
    report = JSON.parse(script.getAttribute('data-report'));

report.unshift(labels)

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper, dataTable;

function drawChart() {
    if(report.length > 1) {
        wrapper = new google.visualization.ChartWrapper({
            chartType: 'BarChart',
            dataTable: google.visualization.arrayToDataTable(report),
            options: {
                chartArea: {
                    width: '70%',
                    left: '5%',
                },
                pointSize: 6,
            },
            containerId: 'chart'
        });

        wrapper.draw();
    } else {
        container = $('#chart');
        container.text('No data.');
    }
}

