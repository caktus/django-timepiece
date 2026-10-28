var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    report = JSON.parse(script.getAttribute('data-report')),
    type = script.getAttribute('data-type');

function drawChart() {
    if (report.length > 1) {
        var rows = report.slice(1);
        if (type === 'week') {
            rows = rows.slice().reverse();
        }
        var labels = rows.map(function (r) { return String(r[0]); });
        var chart_height = Math.max(300, rows.length * 30 + 80);

        var container = document.getElementById('chart');
        container.innerHTML = '';
        var canvas = document.createElement('canvas');
        canvas.style.height = chart_height + 'px';
        container.appendChild(canvas);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: report[0][1],
                        data: rows.map(function (r) { return Number(r[1]) || 0; }),
                        backgroundColor: 'rgba(51, 122, 183, 0.7)'
                    },
                    {
                        label: report[0][2],
                        data: rows.map(function (r) { return Number(r[2]) || 0; }),
                        backgroundColor: 'rgba(153, 102, 255, 0.7)'
                    }
                ]
            },
            options: {
                responsive: false,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Hours' }
                    }
                }
            }
        });
    } else if (report.length === 1) {
        var container = $('#chart'),
            text = $('<p>No data to display.</p>');
        container.append(text);
    }
}

drawChart();
