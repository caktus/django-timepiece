from django.urls import include, path, re_path
from django.contrib.auth import views as auth_views
from django.contrib import admin

admin.autodiscover()  # For Django 1.6


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^selectable/', include('selectable.urls')),
    re_path(r'', include('timepiece.urls')),

    # authentication views
    re_path(r'^accounts/login/$', auth_views.LoginView.as_view(),
        name='auth_login'),
    re_path(r'^accounts/logout/$', auth_views.logout_then_login,
        name='auth_logout'),
    re_path(r'^accounts/password-change/$',
        auth_views.PasswordChangeView.as_view(),
        name='change_password'),
    re_path(r'^accounts/password-change/done/$',
        auth_views.PasswordChangeDoneView.as_view()),
    re_path(r'^accounts/password-reset/$',
        auth_views.PasswordResetView.as_view(),
        name='reset_password'),
    re_path(r'^accounts/password-reset/done/$',
        auth_views.PasswordResetDoneView.as_view()),
    re_path(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view()),
    re_path(r'^accounts/reset/done/$',
        auth_views.PasswordResetCompleteView.as_view()),
]
