import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Sum, get_model, Q
from django.utils import timezone
from django.utils.functional import lazy

from timepiece.defaults import TimepieceDefaults


reverse_lazy = lazy(reverse, str)


defaults = TimepieceDefaults()


class ActiveEntryError(Exception):
    pass


class DecimalEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_setting(name, **kwargs):
    if hasattr(settings, name):
        return getattr(settings, name)
    if hasattr(kwargs, 'default'):
        return kwargs['default']
    if hasattr(defaults, name):
        return getattr(defaults, name)
    msg = '{0} must be specified in your project settings.'.format(name)
    raise AttributeError(msg)


def to_datetime(date):
    """ """
    return datetime.datetime(date.year, date.month, date.day)


def add_timezone(value, tz=None):
    """If the value is naive, then the timezone is added to it.

    If no timezone is given, timezone.get_current_timezone() is used.
    """
    if tz is None:
        tz = timezone.get_current_timezone()
    try:
        if timezone.is_naive(value):
            return timezone.make_aware(value, tz)
    except AttributeError:  # 'datetime.date' object has no attribute 'tzinfo'
        dt = datetime.datetime.combine(value, datetime.time())
        return timezone.make_aware(dt, tz)
    return value


def get_total_time(seconds):
    """
    Returns the specified number of seconds in an easy-to-read HH:MM:SS format
    """
    hours = int(seconds / 3600)
    seconds %= 3600
    minutes = int(seconds / 60)
    seconds %= 60

    return u'%02i:%02i:%02i' % (hours, minutes, seconds)


def get_year_start(from_day=None):
    if not from_day:
        from_day = datetime.date.today()
    from_day = add_timezone(from_day)
    return from_day.replace(month=1).replace(day=1)


def get_month_start(from_day=None):
    if not from_day:
        from_day = datetime.date.today()
    from_day = add_timezone(from_day)
    return from_day.replace(day=1)


def get_week_start(day=None):
    if not day:
        day = datetime.date.today()
    days_since_monday = day.weekday()
    if days_since_monday != 0:
        day = day - datetime.timedelta(days=days_since_monday)
    day = add_timezone(day)
    return day


def get_last_billable_day(day=None):
    if not day:
        day = datetime.date.today()
    day += relativedelta(months=1)
    return get_week_start(get_month_start(day)) - datetime.timedelta(days=1)


def generate_dates(start=None, end=None, by='week'):
    if start:
        start = add_timezone(start)
    if end:
        end = add_timezone(end)
    if by == 'year':
        start = get_year_start(start)
        return rrule.rrule(rrule.YEARLY, dtstart=start, until=end)
    if by == 'month':
        start = get_month_start(start)
        return rrule.rrule(rrule.MONTHLY, dtstart=start, until=end)
    if by == 'week':
        start = get_week_start(start)
        return rrule.rrule(rrule.WEEKLY, dtstart=start, until=end, byweekday=0)
    if by == 'day':
        return rrule.rrule(rrule.DAILY, dtstart=start, until=end)


def get_week_window(day=None):
    """Returns (Monday, Sunday) of the requested week."""
    start = get_week_start(day)
    return (start, start + relativedelta(days=6))


def get_hours(entries):
    hours = {
        'total': 0,
        'billable': 0,
        'non_billable': 0
    }
    for entry in entries:
        hours['total'] += entry['hours']
        if entry['billable']:
            hours['billable'] += entry['hours']
        else:
            hours['non_billable'] += entry['hours']
    return hours


def daily_summary(day_entries):
    projects = {}
    all_day = {}
    for name, entries in groupby(day_entries, lambda x: x['project__name']):
        hours = get_hours(entries)
        projects[name] = hours
        for key in hours.keys():
            if key in all_day:
                all_day[key] += hours[key]
            else:
                all_day[key] = hours[key]

    return (all_day, projects)


def grouped_totals(entries):
    select = {"day": {"date": """DATE_TRUNC('day', end_time)"""},
              "week": {"date": """DATE_TRUNC('week', end_time)"""}}
    weekly = entries.extra(select=select["week"]).values('date', 'billable')
    weekly = weekly.annotate(hours=Sum('hours')).order_by('date')
    daily = entries.extra(select=select["day"]).values('date', 'project__name',
                                                       'billable')
    daily = daily.annotate(hours=Sum('hours')).order_by('date',
                                                        'project__name')
    weeks = {}
    for week, week_entries in groupby(weekly, lambda x: x['date']):
        if week is not None:
            week = add_timezone(week)
        weeks[week] = get_hours(week_entries)
    days = []
    last_week = None
    for day, day_entries in groupby(daily, lambda x: x['date']):
        week = get_week_start(day)
        if last_week and week > last_week:
            yield last_week, weeks.get(last_week, {}), days
            days = []
        days.append((day, daily_summary(day_entries)))
        last_week = week
    yield week, weeks.get(week, {}), days


def get_hour_summaries(hours):
    """
    Coerce totals dictionary or list into a list of ordered tuples with %'s
    """
    if hasattr(hours, 'get'):
        billable = hours.get('billable', 0)
        non_billable = hours.get('non_billable', 0)
        worked = hours.get('total', 0)
    else:
        billable, non_billable, worked = hours
    if worked > 0:
        return [
            (billable, round(billable / worked * 100, 2)),
            (non_billable, round(non_billable / worked * 100, 2)),
            worked,
        ]
    else:
        return [(0, 0), (0, 0), 0]



def get_project_hours_for_week(week_start):
    """
    Gets all ProjectHours entries in the 7-day period beginning on week_start.

    Returns a values set, ordered by the project id.
    """
    week_end = week_start + relativedelta(days=7)
    ProjectHours = get_model('entries', 'ProjectHours')
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
    users = project_hours.values_list('user__id', 'user__first_name',
            'user__last_name').distinct().order_by('user__first_name',
            'user__last_name')
    return users


def get_total_seconds(td):
    """
    The equivalent for datetime.timedelta.total_seconds() for Python 2.6
    """
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


def get_hours_per_week(user):
    """Retrieves the number of hours the user should work per week."""
    UserProfile = get_model('crm', 'UserProfile')
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None
    return profile.hours_per_week if profile else Decimal('40.00')


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


def get_active_entry(user):
    Entry = get_model('entries', 'Entry')
    try:
        entry = Entry.no_join.get(user=user, end_time__isnull=True)
    except Entry.DoesNotExist:
        entry = None
    except Entry.MultipleObjectsReturned:
        raise ActiveEntryError('Only one active entry is allowed.')
    return entry
