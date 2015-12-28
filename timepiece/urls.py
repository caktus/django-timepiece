from django.conf.urls import include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView


urlpatterns = [
    # Redirect the base URL to the dashboard.
    url(r'^$', RedirectView.as_view(url=reverse_lazy('dashboard'), permanent=False)),

    url('', include('timepiece.crm.urls')),
    url('', include('timepiece.contracts.urls')),
    url('', include('timepiece.entries.urls')),
    url('', include('timepiece.reports.urls')),
]
