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
            chartType: 'AreaChart',
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
    } else {
        container = $('#chart');
        container.text('There are no entries which match your query.');
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
    // Add "select all" clickable to the label
    $('a.select').click(function(e) {
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
