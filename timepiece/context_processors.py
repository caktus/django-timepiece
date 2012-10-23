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
    user = request.user
    projects = []
    if user.is_authenticated() and user.is_active:
        vacation_ids = utils.get_setting(
                'TIMEPIECE_PAID_LEAVE_PROJECTS').values()
        vacation_projects = timepiece.Project.objects.filter(
                users=user, id__in=vacation_ids) \
            .order_by('name').values('name', 'id')
        work_projects = timepiece.Project.objects.filter(
                users=user, status__enable_timetracking=True,
                type__enable_timetracking=True) \
            .exclude(id__in=vacation_ids) \
            .order_by('name').values('name', 'id')
        projects = list(work_projects) + list(vacation_projects)

    return {
        'quick_clock_in_projects': projects,
    }


def extra_nav(request):
    return {
        'timepiece_extra_nav': utils.get_setting('TIMEPIECE_EXTRA_NAV'),
    }
