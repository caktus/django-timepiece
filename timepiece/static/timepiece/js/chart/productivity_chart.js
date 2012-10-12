var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var report = JSON.parse(script.getAttribute('data-report'));

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper;

function drawChart() {
    if(report.length > 1) {
        wrapper = new google.visualization.ChartWrapper({
            chartType: 'BarChart',
            dataTable: google.visualization.arrayToDataTable(report),
            options: {
                bar: {
                    groupWidth: '50%'
                },
                chartArea: {
                    top: '5%',
                    bottom: '5%'
                },
                legend: {
                    position: 'bottom'
                }
            },
            containerId: 'chart'
        });
        wrapper.draw();
    } else {
        container = $('#chart');
        container.text('');
    }
}
