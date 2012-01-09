from django.conf.urls.defaults import *
from timepiece.models import Entry
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

    ### time sheets ###
    url(
        r'^time-sheet/projects/$',
        views.tracked_projects,
        name='tracked_projects',
    ),
    url(
        r'^time-sheet/people/$',
        views.tracked_people,
        name='tracked_people',
    ),
    url(r'^reports/$', views.hourly_report, name='hourly_report'),
    url(r'^reports/summary/$', views.summary, name='timepiece-summary'),
    url(r'^reports/payroll/$', views.payroll_summary, name='payroll_summary',),
    url(
        r'^time-sheet/people/create/$',
        views.create_edit_person_time_sheet,
        name='create_person_time_sheet',
    ),
    url(
        r'^time-sheet/people/(?P<person_id>\d+)/edit/$',
        views.create_edit_person_time_sheet,
        name='edit_person_time_sheet',
    ),
    url(
        r'^time-sheet/people/(?P<person_id>\d+)/(period/)?' +
        r'(?:(?P<period_id>\d+)/)?(?:(?P<window_id>\d+)/)?' +
        r'(?:(?P<hourly>hourly)/)?$',
        views.view_person_time_sheet,
        name='view_person_time_sheet',
    ),
    url(
        r'^time-sheet/(?P<action>verify|approve)/' +
        r'(?:(?P<person_id>\d+)/)?(?:(?P<period_id>\d+)/)?' +
        r'(?:(?P<window_id>\d+)/)?$',
        views.time_sheet_change_status,
        name='time_sheet_change_status',
    ),
    url(
        r'time-sheet/invoice-project/(?P<project_id>\d+)/' +
        r'(?P<to_date>\d\d\d\d-\d\d-\d\d)/' +
        r'(?:(?P<from_date>\d\d\d\d-\d\d-\d\d)/)?$',
        views.time_sheet_invoice_project,
        name='time_sheet_invoice_project',
    ),
    url(
        r'^time-sheet/project/(?P<project_id>\d+)/(?:(?P<window_id>\d+)/)?$',
        views.project_time_sheet,
        name='project_time_sheet',
    ),
    url(
        r'^time-sheet/project/(?P<project_id>\d+)/(?:(?P<window_id>\d+)/)' +
        r'?export/$',
        views.export_project_time_sheet,
        name='export_project_time_sheet',
    ),
    url(
        r'^time-sheet/project/invoice-projects/$',
        views.invoice_projects,
        name='invoice_projects',
    ),
    url(
        r'^time-sheet/project/invoices/$',
        views.list_invoices,
        name='list_invoices',
    ),
    url(
        r'^time-sheet/project/invoice/(?P<invoice_id>\d+)/$',
        views.view_invoice,
        name='view_invoice',
    ),
    url(
        r'^projection/$',
        views.projection_summary,
        name='projection_summary',
    ),
    url(
        r'^edit-settings/$',
        views.edit_settings,
        name='edit_settings',
    ),
)
