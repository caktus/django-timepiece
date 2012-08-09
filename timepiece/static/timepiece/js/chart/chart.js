var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1];

var hours = JSON.parse(script.getAttribute('data-hours')),
    dates = JSON.parse(script.getAttribute('data-dates'));

google.load('visualization', '1.0', {'packages':['corechart']});
google.setOnLoadCallback(drawChart);

var wrapper,
    dataTable;

function drawChart() {
    dataTable = processData();

    if(dataTable.length > 1) {
        wrapper = new google.visualization.ChartWrapper({
            chartType: 'ColumnChart',
            dataTable: google.visualization.arrayToDataTable(dataTable),
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

function getIndexOfDate(data, date) {
    for(i = 1; i < data.length; i++) {
        if(data[i][0] === date) {
            return i;
        }
    }
}

function round(x) {
    return Math.round((x * 100)) / 100;
}

function processData() {
    var data = [
        ['Date', 'Non-billable', 'Billable']
    ], i;
   
    for(i = 0; i < dates.length; i++) {
        data.push([dates[i], 0, 0]);
    }
    
    for(var user in hours) {
        var index = 0,
            user_hours = hours[user];

        for(var date in user_hours) {
            index = getIndexOfDate(data, user_hours[date].date);

            data[index][1] += user_hours[date].nonbillable;
            data[index][2] += user_hours[date].billable;
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

                // Need to round the results...
                dataTable[index][1] = round(dataTable[index][1]);
                dataTable[index][2] = round(dataTable[index][2]);
            }
        } else {
            for(date in user) {
                data = user[date];
                index = getIndexOfDate(dataTable, data.date);

                dataTable[index][1] -= data.billable;
                dataTable[index][2] -= data.nonbillable;

                // Need to round the results...
                dataTable[index][1] = round(dataTable[index][1]);
                dataTable[index][2] = round(dataTable[index][2]);
            }
        }

        wrapper.setDataTable(google.visualization.arrayToDataTable(dataTable));
        wrapper.draw();
    });
});