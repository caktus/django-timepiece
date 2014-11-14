var page = require('webpage').create();
var system = require('system');
var fs = require('fs');
var json_filename = system.args[1];
// var data_str = fs.read('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/' + json_filename);
// var data = JSON.parse(data_str);

page.viewportSize = { width: 1600, height: 800 };
page.open('/home/dcbrowne/webapps/djangopt/project_toolbox/timepiece/templates/timepiece/project/burnup_charts/burnup_chart_pdf.html', function(status) {
    if ( status === "success" ) {
        // inject_d3 = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/d3.min.js');
        // inject_c3 = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/c3.min.js');
        // inject_bc = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/burnup_charts.js');
        inject_data = page.injectJs('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/' + json_filename);
        page.evaluate(function() {
            document.body.bgColor = 'white';
            draw_burnup_chart(data);
        });
        setTimeout(function() {
            page.render('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/burnup_chart.png');
            phantom.exit(); 
        }, 2000);
    }
});





// var page = require('webpage').create();
// var system = require('system');
// var fs = require('fs');
// var json_filename = system.args[1];
// console.log('json_filename 1', json_filename);
// var data = JSON.parse(fs.read('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/' + json_filename));
// console.log(data);
// phantom.exit();

// page.open('/home/dcbrowne/webapps/djangopt/project_toolbox/timepiece/templates/timepiece/project/burnup_charts/burnup_chart_pdf.html', function(status) {
//     if ( status === "success" ) {
//         inject_d3 = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/d3.min.js');
//         inject_c3 = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/c3.min.js');
//         inject_bc = page.injectJs('/home/dcbrowne/webapps/staticpt/timepiece/js/burnup_charts/burnup_charts.js');
//         console.log('json_filename 4', json_filename);
//         page.includeJs("http://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js", function() {
//             console.log('json_filename 5', json_filename);
//             page.evaluate(function(json_filename) {
//                 document.body.bgColor = 'white';
//                 console.log('json_filename 6', json_filename);
//                 $.getJSON('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/' + json_filename, function( data ) {
//                     draw_burnupchart(data);
//                     page.render('/home/dcbrowne/webapps/djangopt/project_toolbox/burnup_chart_cache/burnup_chart.pdf');
//                     phantom.exit();
//                 });
//             });
//         });
//     }
// });
