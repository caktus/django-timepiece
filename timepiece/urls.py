from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView


urlpatterns = patterns('',
    # Redirect the base URL to the dashboard.
    url(r'^$', RedirectView.as_view(url=reverse_lazy('dashboard'))),

    url('', include('timepiece.crm.urls')),
    url('', include('timepiece.contracts.urls')),
    url('', include('timepiece.entries.urls')),
    url('', include('timepiece.reports.urls')),
)
