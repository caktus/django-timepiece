from django.conf.urls import patterns, url
from timepiece.reports import views


urlpatterns = patterns('',
    url(r'^hourly/$',
        views.HourlyReport.as_view(),
        name='report_hourly'),

    url(r'^payroll/$',
        views.report_payroll_summary,
        name='report_payroll_summary'),

    url(r'^billable_hours/$',
        views.BillableHours.as_view(),
        name='report_billable_hours'),

    url(r'^productivity/$',
        views.report_productivity,
        name='report_productivity'),
)
