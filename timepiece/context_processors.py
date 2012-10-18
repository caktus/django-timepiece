from timepiece import models as timepiece
from timepiece import utils
from timepiece.forms import QuickSearchForm


def timepiece_settings(request):
    context = {
        'TIMEPIECE_ICON_URL': utils.get_setting('TIMEPIECE_ICON_URL'),
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
        'timepiece_extra_nav': utils.get_setting('TIMEPIECE_EXTRA_NAV'),
    }
    return context
