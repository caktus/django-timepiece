from django.conf.urls import url

from timepiece.entries import views


urlpatterns = [
    url(r'^dashboard/(?:(?P<active_tab>progress|all-entries|online-users)/)?$',
        views.Dashboard.as_view(),
        name='dashboard'),

    # Active entry
    url(r'^entry/clock_in/$',
        views.clock_in,
        name='clock_in'),
    url(r'^entry/clock_out/$',
        views.clock_out,
        name='clock_out'),
    url(r'^entry/toggle_pause/$',
        views.toggle_pause,
        name='toggle_pause'),

    # Entries
    url(r'^entry/add/$',
        views.create_edit_entry,
        name='create_entry'),
    url(r'^entry/(?P<entry_id>\d+)/edit/$',
        views.create_edit_entry,
        name='edit_entry'),
    url(r'^entry/(?P<entry_id>\d+)/reject/$',
        views.reject_entry,
        name='reject_entry'),
    url(r'^entry/(?P<entry_id>\d+)/delete/$',
        views.delete_entry,
        name='delete_entry'),

    # Schedule
    url(r'^schedule/$',
        views.ScheduleView.as_view(),
        name='view_schedule'),
    url(r'^schedule/edit/$',
        views.EditScheduleView.as_view(),
        name='edit_schedule'),
    url(r'^schedule/ajax/$',
        views.ScheduleAjaxView.as_view(),
        name='ajax_schedule'),
    url(r'^schedule/ajax/(?P<assignment_id>\d+)/$',
        views.ScheduleDetailView.as_view(),
        name='ajax_schedule_detail'),
]
