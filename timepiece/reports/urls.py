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
)
