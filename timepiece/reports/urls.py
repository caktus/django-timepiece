from django.urls import re_path

from timepiece.reports import views


urlpatterns = [
    re_path(r'^reports/hourly/$',
            views.HourlyReport.as_view(),
            name='report_hourly'),

    re_path(r'^reports/payroll/$',
            views.ReportPayrollSummary.as_view(),
            name='report_payroll_summary'),

    re_path(r'^reports/billable_hours/$',
            views.BillableHours.as_view(),
            name='report_billable_hours'),

    re_path(r'^reports/productivity/$',
            views.report_productivity,
            name='report_productivity'),

    re_path(r'^reports/estimation_accuracy/$',
            views.report_estimation_accuracy,
            name='report_estimation_accuracy'),
]
