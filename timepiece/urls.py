try:
    from django.conf.urls import patterns, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, include, url

from timepiece import views


urlpatterns = patterns('',
    url(r'^$', views.view_entries, name='timepiece-entries'),
    url(r'^period/(?P<delta>\d+)/$', views.view_entries,
        name='timepiece-previous-entries'),
    url(r'^clockin/$', views.clock_in, name='timepiece-clock-in'),
    url(r'^clockout/(?P<entry_id>\d+)/$', views.clock_out,
        name='timepiece-clock-out'),
    url(r'^toggle/(?P<entry_id>\d+)/$', views.toggle_paused,
        name='timepiece-toggle-paused'),
    url(r'^add/$', views.create_edit_entry, name='timepiece-add'),
    url(r'^update/(?P<entry_id>\d+)/$', views.create_edit_entry,
        name='timepiece-update'),
    url(r'^reject/(?P<entry_id>\d+)/$', views.reject_entry,
        name='timepiece-reject-entry'),
    url(r'^delete/(?P<entry_id>\d+)/$', views.delete_entry,
        name='timepiece-delete'),
    url(r'^search/$', views.quick_search, name='quick_search'),

    url(r'^person/list/$', views.list_people, name='list_people'),
    url(
        r'^person/(?P<person_id>\d+)/$',
        views.view_person,
        name='view_person',
    ),
    url(
        r'^person/create/$',
        views.create_edit_person,
        name='create_person',
    ),
    url(
        r'^person/(?P<person_id>\d+)/edit/$',
        views.create_edit_person,
        name='edit_person',
    ),
    url(r'^business/list/$', views.list_businesses, name='list_businesses'),
    url(
        r'^business/create/$',
        views.create_edit_business,
        name='create_business',
    ),
    url(
        r'^business/(?P<business>\d+)/$',
        views.view_business,
        name='view_business',
    ),
    url(
        r'^business/(?P<business>\d+)/edit/$',
        views.create_edit_business,
        name='edit_business',
    ),
    url(r'^project/list/$', views.list_projects, name='list_projects'),
    url(
        r'^project/(?P<project_id>\d+)/$',
        views.view_project,
        name='view_project',
    ),
    url(
        r'^project/create/$',
        views.create_edit_project,
        name='create_project',
    ),
    url(
        r'^project/(?P<project_id>\d+)/edit/$',
        views.create_edit_project,
        name='edit_project',
    ),
    url(
        r'^project/(?P<project_id>\d+)/user/add/$',
        views.add_user_to_project,
        name='add_user_to_project',
    ),
    url(
        r'^project/(?P<project_id>\d+)/user/(?P<user_id>\d+)/remove/$',
        views.remove_user_from_project,
        name='remove_user_from_project',
    ),
    url(
        r'^project/(?P<project_id>\d+)/user/(?P<user_id>\d+)/edit/$',
        views.edit_project_relationship,
        name='edit_project_relationship',
    ),


    url(
        r'^project/(?P<pk>\d+)/delete/$',
        views.DeleteProjectView.as_view(),
        name='delete_project',
    ),
    url(
        r'^business/(?P<pk>\d+)/delete/$',
        views.DeleteBusinessView.as_view(),
        name='delete_business',
    ),
    url(
        r'^person/(?P<pk>\d+)/delete/$',
        views.DeletePersonView.as_view(),
        name='delete_person',
    ),

    ### time sheets ###

    # Reports
    url(
        r'^reports/$',
        views.HourlyReport.as_view(),
        name='hourly_report',
    ),
    url(
        r'^reports/summary/$',
        views.summary,
        name='timepiece-summary',
    ),
    url(
        r'^reports/payroll/$',
        views.payroll_summary,
        name='payroll_summary',
    ),
    url(
        r'^reports/billable/$',
        views.BillableHours.as_view(),
        name='billable_hours',
    ),

    # People
    url(
        r'time-sheet/people/(?P<user_id>\d+)/$',
        views.view_person_time_sheet,
        name='view_person_time_sheet',
    ),
    url(
        r'^time-sheet/reject/(?P<user_id>\d+)/$',
        views.reject_entries,
        name='timepiece-reject-entries',
    ),
    url(
        r'^time-sheet/(?P<action>verify|approve)/(?P<user_id>\d+)/' +
        r'(?P<from_date>\d\d\d\d-\d\d-\d\d)/$',
        views.change_person_time_sheet,
        name='change_person_time_sheet',
    ),

    # Projects
    url(
        r'^time-sheet/project/(?P<pk>\d+)/$',
        views.ProjectTimesheet.as_view(),
        name='project_time_sheet',
    ),
    url(
        r'^time-sheet/project/(?P<pk>\d+)/csv/$',
        views.ProjectTimesheetCSV.as_view(),
        name='export_project_time_sheet',
    ),
    url(
        r'^edit-settings/$',
        views.edit_settings,
        name='edit_settings',
    ),

    ### Invoices ###
    url(
        r'^invoice/outstanding/$',
        views.invoice_projects,
        name='invoice_projects',
    ),
    url(
        r'invoice/project/(?P<project_id>\d+)/create/' +
        r'(?P<to_date>\d\d\d\d-\d\d-\d\d)/' +
        r'(?:(?P<from_date>\d\d\d\d-\d\d-\d\d)/)?$',
        views.confirm_invoice_project,
        name='confirm_invoice_project',
    ),
    url(
        r'^invoice/list/$',
        views.list_invoices,
        name='list_invoices',
    ),
    url(
        r'^invoice/(?P<pk>\d+)/$',
        views.InvoiceDetail.as_view(),
        name='view_invoice',
    ),
    url(
        r'^invoice/(?P<pk>\d+)/entries/$',
        views.InvoiceEntryDetail.as_view(),
        name='view_invoice_entries',
    ),
    url(
        r'^invoice/(?P<pk>\d+)/csv/$',
        views.InvoiceCSV.as_view(),
        name='view_invoice_csv',
    ),
    url(
        r'^invoice/edit/(?P<pk>\d+)/$',
        views.InvoiceEdit.as_view(),
        name='edit_invoice',
    ),
    url(
        r'^invoice/delete/(?P<pk>\d+)/$',
        views.InvoiceDelete.as_view(),
        name='delete_invoice',
    ),
    url(
        r'^invoice/remove-entry/(?P<invoice_id>\d+)/(?P<entry_id>\d+)/$',
        views.remove_invoice_entry,
        name='remove_invoice_entry',
    ),
    # contracts
    url(
        r'^contract/(?P<pk>\d+)/$',
        views.ContractDetail.as_view(),
        name='view_contract',
    ),
    url(
        r'^contract/list/$',
        views.ContractList.as_view(),
        name='list_contracts',
    ),
    # project hours
    url(
        r'^schedule/$',
        views.ProjectHoursView.as_view(),
        name='project_hours',
    ),
    url(
        r'^schedule/edit/$',
        views.EditProjectHoursView.as_view(),
        name='edit_project_hours',
    ),

    # ajax views
    url(
        r'^ajax/hours/$',
        views.ProjectHoursAjaxView.as_view(),
        name='project_hours_ajax_view',
    ),
    url(
        r'^ajax/hours/(?P<pk>\d+)/$',
        views.ProjectHoursDetailView.as_view(),
        name='project_hours_detail_view',
    ),
)
