from django.conf.urls.defaults import *
from pendulum.models import Entry
from pendulum import views

urlpatterns = patterns('',
    url(r'^$', views.view_entries, name='pendulum-entries'),
    url(r'^period/(?P<delta>\d+)/$', views.view_entries, name='pendulum-previous-entries'),
    url(r'^clockin/$', views.clock_in, name='pendulum-clock-in'),
    url(r'^clockout/(?P<entry_id>\d+)/$', views.clock_out, name='pendulum-clock-out'),
    url(r'^toggle/(?P<entry_id>\d+)/$', views.toggle_paused, name='pendulum-toggle-paused'),
    url(r'^add/$', views.add_entry, name='pendulum-add'),
    url(r'^update/(?P<entry_id>\d+)/$', views.update_entry, name='pendulum-update'),
    url(r'^delete/(?P<entry_id>\d+)/$', views.delete_entry, name='pendulum-delete'),
    
    url(r'^summary/', views.summary, name='pendulum-summary'),
)
