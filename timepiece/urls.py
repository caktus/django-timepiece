from django.conf.urls.defaults import *
from timepiece.models import Entry
from timepiece import views

urlpatterns = patterns('',
    url(r'^$', views.view_entries, name='timepiece-entries'),
    url(r'^period/(?P<delta>\d+)/$', views.view_entries, name='timepiece-previous-entries'),
    url(r'^clockin/$', views.clock_in, name='timepiece-clock-in'),
    url(r'^clockout/(?P<entry_id>\d+)/$', views.clock_out, name='timepiece-clock-out'),
    url(r'^toggle/(?P<entry_id>\d+)/$', views.toggle_paused, name='timepiece-toggle-paused'),
    url(r'^add/$', views.create_edit_entry, name='timepiece-add'),
    url(r'^update/(?P<entry_id>\d+)/$', views.create_edit_entry, name='timepiece-update'),
    url(r'^delete/(?P<entry_id>\d+)/$', views.delete_entry, name='timepiece-delete'),
    url(r'^summary/', views.summary, name='timepiece-summary'),


    url(r'^project/list/$', views.list_projects, name='list_projects'),
    url(
        r'^business/(?P<business_id>\d+)/project/(?P<project_id>\d+)/$',
        views.view_project,
        name='view_project',
    ),
    url(
        r'^(?:business/(?P<business_id>\d+)/)?project/create/$',
        views.create_edit_project,
        name='create_project',
    ),
    url(
        r'^business/(?P<business_id>\d+)/project/(?P<project_id>\d+)/edit/$',
        views.create_edit_project,
        name='edit_project',
    ),
    url(
        r'^business/(?P<business_id>\d+)/project/(?P<project_id>\d+)/contact/(?P<user_id>\d+)/edit/$',
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
        r'^time-sheet/people/(?P<person_id>\d+)/period/(?P<period_id>\d+)/(?:(?P<window_id>\d+)/)?$',
        views.view_person_time_sheet,
        name='view_person_time_sheet',
    ),
    url(
        r'^time-sheet/project/(?P<project_id>\d+)/(?:(?P<window_id>\d+)/)?$',
        views.project_time_sheet,
        name='project_time_sheet',
    ),
    url(
        r'^time-sheet/project/(?P<project_id>\d+)/(?:(?P<window_id>\d+)/)?export/$',
        views.export_project_time_sheet,
        name='export_project_time_sheet',
    ),

    url(
        r'^payroll/summary/$',
        views.payroll_summary,
        name='payroll_summary',
    ),

    url(
        r'^projection/$',
        views.projection_summary,
        name='projection_summary',
    ),

        url(
        r'^my_weekly_projection/$',
        views.this_week,
        name='this_week',
    ),
)

