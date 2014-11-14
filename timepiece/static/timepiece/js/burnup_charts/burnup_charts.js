function draw_burnup_chart(data, project_id) {
    var chart = c3.generate({
        bindto: '#burnup-chart-' + project_id,
        data: {
            x: 'plot_dates',
    //        xFormat: '%Y%m%d', // 'xFormat' can be used as custom format of 'x'
            columns: [
                data.plot_dates,
    //            ['x', '20130101', '20130102', '20130103', '20130104', '20130105', '20130106'],
                // ['proj_mgmt_target', 35, 35, 35, 35, 35, 35],
                // ['proj_dev_target', 100, 100, 100, 100, 100, 100],
                // ['tech_writing_target', 65, 65, 65, 65, 65, 65],
                // ['other_target', 27, 27, 27, 27, 27, 27],
                data.project_management,
                data.project_development,
                data.tech_writing,
                data.other,
                data.activity_goals[0],
                data.activity_goals[1],
                data.activity_goals[2],
                data.activity_goals[3],
                // ['proj_mgmt_actual', 5, 10, 20],
                // ['proj_dev_actual', 20, 40, 65],
                // ['tech_writing_actual', 5, 15, 30],
                // ['other_actual', 3, 12, 15],
            ],
            names: {
                proj_mgmt_target: 'Proj Mgmt Target',
                proj_dev_target: 'Proj Dev Target',
                tech_writing_target: 'Tech Writing Target',
                other_target: 'Other Target',
                today: 'today',
                proj_mgmt_actual: 'Proj Mgmt Actual',
                proj_dev_actual: 'Proj Dev Actual',
                tech_writing_actual: 'Tech Writing Actual',
                other_actual: 'Other Actual',
            },
            colors: {
                proj_mgmt_target: '#1f77b4',
                proj_dev_target: '#ff0000',
                tech_writing_target: '#aaaaaa',
                other_target: '#000000',
                proj_mgmt_actual: '#1f77b4',
                proj_dev_actual: '#ff0000',
                tech_writing_actual: '#aaaaaa',
                other_actual: '#000000',
            },
            regions: {
                proj_mgmt_actual: [{'style': 'dotted'}],
                proj_dev_actual: [{'style': 'dotted'}],
                tech_writing_actual: [{'style': 'dotted'}],
                other_actual: [{'style': 'dotted'}],
            }
        },
        grid: {
            x: {
                // lines: [{value: '2013-01-02', class: 'proj_mgmt_due', text: 'Project Management'},
                //         {value: '2013-01-03', class: 'proj_dev_due', text: 'Project Development'},
                //         {value: '2013-01-05', class: 'tech_writing_due', text: 'Tech Writing'},
                //         {value: '2013-01-06', class: 'other_due', text: 'Tech Writing'},
                //         {value: '2013-01-04', class: 'today', text: 'TODAY'}]
                lines: data.milestones,
            },
            // y: {
            //     lines: [{value: 500}, {value: 800, class: 'grid800', text: 'LABEL 800'}]
            // }
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%Y-%m-%d'
                }
            },
            y: {
                label: { // ADD
                    text: 'Hours',
                    position: 'outer-middle'
                }
          },
        },
        point: {
            show: false
        },
    });
}

function create_burnup_chart(project_id) {
    $.getJSON( '/timepiece/project/' + project_id + '/burnup_chart_data/', function( data ) {
        draw_burnup_chart(data, project_id);
    });
}
