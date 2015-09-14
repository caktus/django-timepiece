"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
import timepiece

urlpatterns = [
    # Examples:
    # url(r'^$', 'mysite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^selectable/', include('selectable.urls')),
    url(r'', include('timepiece.urls')),

    url(r'^accounts/profile/$', timepiece.crm.views.EditSettings.as_view(),
        name='edit_settings'),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        name='auth_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login',
        name='auth_logout'),
    url(r'^accounts/password-change/$',
        'django.contrib.auth.views.password_change',
        name='password_change'),
    url(r'^accounts/password-change/done/$',
        'django.contrib.auth.views.password_change_done',
        name='password_change_done'),
    url(r'^accounts/password-reset/$',
        'django.contrib.auth.views.password_reset',
        name='password_reset'),
    url(r'^accounts/password-reset/done/$',
        'django.contrib.auth.views.password_reset_done',
        name='password_reset_done'),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm'),
    url(r'^accounts/reset/done/$',
        'django.contrib.auth.views.password_reset_complete'),
]
