var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    hours = JSON.parse(script.getAttribute('data-hours'));

function drawChart() {
    if (hours.length < 2) {
        return;
    }
    var labels = hours.slice(1).map(function (row) { return row[0]; });
    var series = [
        {
            label: hours[0][1],
            data: hours.slice(1).map(function (row) { return Number(row[1]) || 0; }),
            borderColor: '#5cb85c',
            backgroundColor: 'rgba(92, 184, 92, 0.6)'
        },
        {
            label: hours[0][2],
            data: hours.slice(1).map(function (row) { return Number(row[2]) || 0; }),
            borderColor: '#da4f49',
            backgroundColor: 'rgba(218, 79, 73, 0.6)'
        }
    ];
    series.forEach(function (s) {
        s.fill = true;
        s.pointRadius = 3;
        s.tension = 0;
    });

    var container = document.getElementById('chart');
    var canvas = document.createElement('canvas');
    container.innerHTML = '';
    container.appendChild(canvas);

    new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: series },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { position: 'bottom' } },
            scales: {
                x: { stacked: true },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: { display: true, text: 'Hours' }
                }
            }
        }
    });
}

drawChart();

$(function() {
    // Add "select all" and "select none" clickable links to form labels.

    $('a.select-all').click(function(e) {
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
