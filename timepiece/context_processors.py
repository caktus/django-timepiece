from timepiece import models as timepiece
from timepiece import utils
from timepiece.forms import QuickSearchForm, QuickClockInForm


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


def quick_clock_in(request):
    form = QuickClockInForm(request.GET or None, user=request.user) \
        if request.user.is_authenticated() else None
    return {
        'quick_clock_in_form': form,
    }


def extra_nav(request):
    return {
        'timepiece_extra_nav': utils.get_setting('TIMEPIECE_EXTRA_NAV'),
    }
