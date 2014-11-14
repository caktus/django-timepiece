from django.conf.urls import patterns, url
from timepiece.reports import views


urlpatterns = patterns('',
    url(r'^reports/hourly/$',
        views.HourlyReport.as_view(),
        name='report_hourly'),

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

    url(r'^reports/backlog/$',
        views.report_backlog,
        name='report_backlog'),

    url(r'^reports/backlog/(?P<user_id>\d+)/$',
        views.report_employee_backlog,
        name='report_employee_backlog'),

    url(r'^reports/active_project_burnup_charts/$',
        views.active_projects_burnup_charts,
        name='report_active_projects_burnup_charts'),

    url(r'^reports/active_project_burnup_charts/(?P<minder_id>\d+)/$',
        views.active_projects_burnup_charts,
        name='report_active_projects_burnup_charts_minder'),
)
