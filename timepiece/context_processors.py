from django.conf import settings

from timepiece import models as timepiece
from timepiece.forms import QuickSearchForm


def timepiece_settings(request):
    default_famfamfam_url = settings.STATIC_URL + 'images/icons/'
    famfamfam_url = getattr(settings, 'FAMFAMFAM_URL', default_famfamfam_url)
    context = {
        'FAMFAMFAM_URL': famfamfam_url,
    }
    return context


def quick_search(request):
    return {
        'quick_search_form': QuickSearchForm(),
    }


def active_entries(request):
    active_entries = None

    if request.user.is_authenticated():
        active_entries = timepiece.Entry.objects.filter(
            end_time__isnull=True,
        ).exclude(
            user=request.user,
        ).select_related('user', 'project', 'activity')

    return {
        'active_entries': active_entries,
    }


def extra_nav(request):
    context = {
        'extra_nav': getattr(settings, 'EXTRA_NAV', {})
    }
    return context
