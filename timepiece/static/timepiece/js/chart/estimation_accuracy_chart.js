var scripts = document.getElementsByTagName('script'),
    script = scripts[scripts.length - 1],
    data = JSON.parse(script.getAttribute('data')),
    chart_max = JSON.parse(script.getAttribute('chart_max'));

function linearRegression(points) {
    var n = points.length,
        sx = 0, sy = 0, sxy = 0, sxx = 0, i, p;
    for (i = 0; i < n; i++) {
        p = points[i];
        sx += p.x;
        sy += p.y;
        sxy += p.x * p.y;
        sxx += p.x * p.x;
    }
    var denom = n * sxx - sx * sx;
    var slope = denom === 0 ? 0 : (n * sxy - sx * sy) / denom;
    var intercept = n === 0 ? 0 : (sy - slope * sx) / n;
    return [slope, intercept];
}

function drawChart() {
    if (data.length > 1) {
        // Column 3 is the mouse-over label for each point.
        var points = data.slice(1).map(function (r) {
            return { x: Number(r[0]) || 0, y: Number(r[1]) || 0, label: r[2] };
        });
        var reg = linearRegression(points),
            slope = reg[0],
            intercept = reg[1],
            maxV = chart_max || 0;

        var container = document.getElementById('chart');
        container.innerHTML = '';
        var canvas = document.createElement('canvas');
        canvas.style.height = '500px';
        container.appendChild(canvas);

        new Chart(canvas, {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        label: 'Contracts',
                        data: points,
                        backgroundColor: 'rgba(51, 122, 183, 0.7)',
                        pointRadius: 5
                    },
                    {
                        type: 'line',
                        label: 'Trend',
                        data: [
                            { x: 0, y: intercept },
                            { x: maxV, y: slope * maxV + intercept }
                        ],
                        borderColor: 'rgba(128, 0, 128, 0.5)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: false,
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            title: function (items) {
                                var pt = points[items[0].dataIndex];
                                return pt ? pt.label : '';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        min: 0,
                        max: maxV,
                        title: { display: true, text: 'Target Hours' }
                    },
                    y: {
                        min: 0,
                        max: maxV,
                        title: { display: true, text: 'Actual Hours' }
                    }
                }
            }
        });
    }
}

drawChart();
