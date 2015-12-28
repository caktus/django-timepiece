from django.conf.urls import include, url
from django.contrib.auth import views as auth_views
from django.contrib import admin

admin.autodiscover()  # For Django 1.6


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^selectable/', include('selectable.urls')),
    url(r'', include('timepiece.urls')),

    # authentication views
    url(r'^accounts/login/$', auth_views.login,
        name='auth_login'),
    url(r'^accounts/logout/$', auth_views.logout_then_login,
        name='auth_logout'),
    url(r'^accounts/password-change/$',
        auth_views.password_change,
        name='change_password'),
    url(r'^accounts/password-change/done/$',
        auth_views.password_change_done),
    url(r'^accounts/password-reset/$',
        auth_views.password_reset,
        name='reset_password'),
    url(r'^accounts/password-reset/done/$',
        auth_views.password_reset_done),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm),
    url(r'^accounts/reset/done/$',
        auth_views.password_reset_complete),
]
