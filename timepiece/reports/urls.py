from django.conf.urls import patterns, url
from timepiece.reports import views


urlpatterns = patterns('',
    url(r'^reports/hourly/$',
        views.HourlyReport.as_view(),
        name='report_hourly'),

    url(r'^reports/writedowns/$',
        views.WritedownReport.as_view(),
        name='report_writedowns'),

    url(r'^reports/payroll/$',
        views.report_payroll_summary,
        name='report_payroll_summary'),

    url(r'^reports/billable_hours/$',
        views.BillableHours.as_view(),
        name='report_billable_hours'),

    url(r'^reports/productivity/$',
        views.report_productivity,
        name='report_productivity'),

    url(r'^reports/estimation_accuracy/$',
        views.report_estimation_accuracy,
        name='report_estimation_accuracy'),

    url(r'^reports/backlog/(?:(?P<active_tab>company|individual-summary|individual-details)/)?$',
        views.report_backlog,
        name='report_backlog'),

    url(r'^reports/backlog/activity/(?P<activity_id>\d+)/$',
        views.report_activity_backlog,
        name='report_activity_backlog'),

    url(r'^reports/backlog/user/(?P<user_id>\d+)/$',
        views.report_employee_backlog,
        name='report_employee_backlog'),

    url(r'^reports/backlog/user/(?P<user_id>\d+)/chart_data/$',
        views.employee_backlog_chart_data,
        name='employee_backlog_chart_data'),

    url(r'^reports/active_project_burnup_charts/$',
        views.active_projects_burnup_charts,
        name='report_active_projects_burnup_charts'),

    url(r'^reports/active_project_burnup_charts/(?P<minder_id>\d+)/$',
        views.active_projects_burnup_charts,
        name='report_active_projects_burnup_charts_minder'),
)
