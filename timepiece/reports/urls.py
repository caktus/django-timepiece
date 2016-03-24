from django.conf.urls import url

from timepiece.reports import views


urlpatterns = [
    url(r'^reports/hourly/$',
        views.HourlyReport.as_view(),
        name='report_hourly'),

    url(r'^reports/payroll/$',
        views.ReportPayrollSummary.as_view(),
        name='report_payroll_summary'),

    url(r'^reports/payroll/csv/$',
        views.ReportPayrollSummaryCSV.as_view(),
        name='report_payroll_summary_csv'),

    url(r'^reports/billable_hours/$',
        views.BillableHours.as_view(),
        name='report_billable_hours'),

    url(r'^reports/productivity/$',
        views.report_productivity,
        name='report_productivity'),

    url(r'^reports/estimation_accuracy/$',
        views.report_estimation_accuracy,
        name='report_estimation_accuracy'),
]
