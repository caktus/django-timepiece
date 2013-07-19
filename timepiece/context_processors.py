from django.db.models import Q
from django.conf import settings

from timepiece import utils
from timepiece.crm.forms import QuickSearchForm

from timepiece.crm.models import Project
from timepiece.entries.models import Entry


def quick_search(request):
    return {
        'quick_search_form': QuickSearchForm(),
    }


def quick_clock_in(request):
    user = request.user
    work_projects = []
    leave_projects = []

    if user.is_authenticated() and user.is_active:
        # Display all active paid leave projects that the user is assigned to.
        leave_ids = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values()
        lq = Q(users=user) & Q(id__in=leave_ids)
        leave_projects = Project.trackable.filter(lq).order_by('name')

        # Get all projects this user has clocked in to.
        entries = Entry.objects.filter(user=user)
        project_ids = list(entries.values_list('project', flat=True))

        # Narrow to projects which can still be clocked in to.
        pq = Q(id__in=project_ids)
        valid_projects = Project.trackable.filter(pq).exclude(id__in=leave_ids)
        valid_ids = list(valid_projects.values_list('id', flat=True))

        # Display the 10 projects this user most recently clocked into.
        work_ids = []
        for i in project_ids:
            if len(work_ids) > 10:
                break
            if i in valid_ids and i not in work_ids:
                work_ids.append(i)
        work_projects = [valid_projects.get(pk=i) for i in work_ids]

    return {
        'leave_projects': leave_projects,
        'work_projects': work_projects,
    }


def extra_settings(request):
    return {
        'COMPRESS_ENABLED': settings.COMPRESS_ENABLED,
    }
