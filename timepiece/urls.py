from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView


urlpatterns = [
    # Redirect the base URL to the dashboard.
    path(r'', RedirectView.as_view(url=reverse_lazy('dashboard'), permanent=False)),
    path('', include('timepiece.crm.urls')),
    path('', include('timepiece.contracts.urls')),
    path('', include('timepiece.entries.urls')),
    path('', include('timepiece.reports.urls')),
]
