from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import get_model, Q


def get_hours_per_week(user):
    """Retrieves the number of hours the user should work per week."""
    UserProfile = get_model('crm', 'UserProfile')
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None
    return profile.hours_per_week if profile else Decimal('40.00')


def get_project_hours_for_week(week_start):
    """
    Gets all ProjectHours entries in the 7-day period beginning on week_start.

    Returns a values set, ordered by the project id.
    """
    ProjectHours = get_model('entries', 'ProjectHours')

    week_end = week_start + relativedelta(days=7)
    qs = ProjectHours.objects.filter(week_start__gte=week_start,
            week_start__lt=week_end)
    qs = qs.values('project__id', 'project__name', 'user__id',
            'user__first_name', 'user__last_name', 'hours')
    qs = qs.order_by('-project__type__billable', 'project__name',)
    return qs


def get_users_from_project_hours(project_hours):
    """
    Gets a list of the distinct users included in the project hours entries,
    ordered by name.
    """
    name = ('user__first_name', 'user__last_name')
    users = project_hours.values_list('user__id', *name).distinct()\
                         .order_by(*name)
    return users


def process_progress(entries, assignments):
    """
    Returns a list of progress summary data (pk, name, hours worked, and hours
    assigned) for each project either worked or assigned.
    The list is ordered by project name.
    """
    Project = get_model('crm', 'Project')
    ProjectHours = get_model('entries', 'ProjectHours')

    # Determine all projects either worked or assigned.
    project_q = Q(id__in=assignments.values_list('project__id', flat=True))
    project_q |= Q(id__in=entries.values_list('project__id', flat=True))
    projects = Project.objects.filter(project_q).select_related('business')

    # Hours per project.
    project_data = {}
    for project in projects:
        try:
            assigned = assignments.get(project__id=project.pk).hours
        except ProjectHours.DoesNotExist:
            assigned = Decimal('0.00')
        project_data[project.pk] = {
            'project': project,
            'assigned': assigned,
            'worked': Decimal('0.00'),
        }

    for entry in entries:
        pk = entry.project_id
        hours = Decimal('%.2f' % round(entry.get_total_seconds() / 3600.0, 2))
        project_data[pk]['worked'] += hours

    # Sort by maximum of worked or assigned hours (highest first).
    key = lambda x: x['project'].name.lower()
    project_progress = sorted(project_data.values(), key=key)

    return project_progress
