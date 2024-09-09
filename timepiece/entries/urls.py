from django.urls import re_path

from timepiece.entries import views


urlpatterns = [
    re_path(r'^dashboard/(?:(?P<active_tab>progress|all-entries|online-users)/)?$',
            views.Dashboard.as_view(),
            name='dashboard'),

    # Active entry
    re_path(r'^entry/clock_in/$',
            views.clock_in,
            name='clock_in'),
    re_path(r'^entry/clock_out/$',
            views.clock_out,
            name='clock_out'),
    re_path(r'^entry/toggle_pause/$',
            views.toggle_pause,
            name='toggle_pause'),

    # Entries
    re_path(r'^entry/add/$',
            views.create_edit_entry,
            name='create_entry'),
    re_path(r'^entry/(?P<entry_id>\d+)/edit/$',
            views.create_edit_entry,
            name='edit_entry'),
    re_path(r'^entry/(?P<entry_id>\d+)/reject/$',
            views.reject_entry,
            name='reject_entry'),
    re_path(r'^entry/(?P<entry_id>\d+)/delete/$',
            views.delete_entry,
            name='delete_entry'),

    # Schedule
    re_path(r'^schedule/$',
            views.ScheduleView.as_view(),
            name='view_schedule'),
    re_path(r'^schedule/edit/$',
            views.EditScheduleView.as_view(),
            name='edit_schedule'),
    re_path(r'^schedule/ajax/$',
            views.ScheduleAjaxView.as_view(),
            name='ajax_schedule'),
    re_path(r'^schedule/ajax/(?P<assignment_id>\d+)/$',
            views.ScheduleDetailView.as_view(),
            name='ajax_schedule_detail'),
]
