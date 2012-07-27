var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var billable = JSON.parse(script.getAttribute('data-billable')),
    nonbillable = JSON.parse(script.getAttribute('data-nonbillable')),
    hours = JSON.parse(script.getAttribute('data-hours'));

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper;

function drawChart() {
    var data = processData();

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

function processData() {
    var data = [
        ['Date', 'Billable', 'Non-billable']
    ], i;

    function getIndexOfDate(date) {
        for(i = 1; i < data.length; i++) {
            if(data[i][0] === date) {
                return i;
            }
        }
    }

    function round(x) {
        return Math.round((x * 100)) / 100;
    }
   
    for(i = 0; i < hours.dates.length; i++) {
        data.push([hours.dates[i], 0, 0]);
    }
    
    for(var user in hours) {
        if(user === 'dates') {
            continue;
        }

        var index = 0,
            dates = hours[user];

        for(var date in dates) {
            index = getIndexOfDate(dates[date].date);

            data[index][1] += dates[date].billable;
            data[index][2] += dates[date].nonbillable;
        }
    }

    for(i = 1; i < data.length; i++) {
        data[i][1] = round(data[i][1]);
        data[i][2] = round(data[i][2]);
    }
    
    return data;
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