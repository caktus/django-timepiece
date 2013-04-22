from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect

from django.conf.urls import patterns, include, url

from timepiece import views


urlpatterns = patterns('',
    # Redirect the base URL to the dashboard.
    url(r'^$', lambda r: HttpResponsePermanentRedirect(reverse('dashboard'))),

    url('', include('timepiece.crm.urls')),
    url('', include('timepiece.contracts.urls')),
    url('', include('timepiece.entries.urls')),
    url('', include('timepiece.reports.urls')),

    url(r'^search/$', views.search, name='search'),
)
