var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var hours = JSON.parse(script.getAttribute('data-hours'));

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper,
    dataTable;

function drawChart() {
    dataTable = processData();

    wrapper = new google.visualization.ChartWrapper({
        chartType: 'LineChart',
        dataTable: google.visualization.arrayToDataTable(dataTable),
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

function getIndexOfDate(data, date) {
    for(i = 1; i < data.length; i++) {
        if(data[i][0] === date) {
            return i;
        }
    }
}

function processData() {
    var data = [
        ['Date', 'Billable', 'Non-billable']
    ], i;

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
            index = getIndexOfDate(data, dates[date].date);

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
        var user = hours[$(this).attr('id')],
            date, data, index;

        if($(this).attr('checked') === 'checked') {
            for(date in user) {
                data = user[date];
                index = getIndexOfDate(dataTable, data.date);

                dataTable[index][1] += data.billable;
                dataTable[index][2] += data.nonbillable;
            }
        } else {
            for(date in user) {
                data = user[date];
                index = getIndexOfDate(dataTable, data.date);

                dataTable[index][1] -= data.billable;
                dataTable[index][2] -= data.nonbillable;
            }
        }

        wrapper.setDataTable(google.visualization.arrayToDataTable(dataTable));
        wrapper.draw();
    });
});