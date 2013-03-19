import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Sum, get_model, Q
from django.utils.functional import lazy

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

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


def find_overtime(dates):
    """Given a list of weekly summaries, return the overtime for each week"""
    return sum([day - 40 for day in dates if day > 40])


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


def date_totals(entries, by):
    """Yield a user's name and a dictionary of their hours"""
    date_dict = {}
    for date, date_entries in groupby(entries, lambda x: x['date']):
        if isinstance(date, datetime.datetime):
            date = date.date()
        d_entries = list(date_entries)

        if by == 'user':
            name = ' '.join((d_entries[0]['user__first_name'],
                    d_entries[0]['user__last_name']))
        elif by == 'project':
            name = d_entries[0]['project__name']
        else:
            name = d_entries[0][by]

        pk = d_entries[0][by]
        hours = get_hours(d_entries)
        date_dict[date] = hours
    return name, pk, date_dict


def project_totals(entries, date_headers, hour_type=None, overtime=False,
                   total_column=False, by='user'):
    """
    Yield hour totals grouped by user and date. Optionally including overtime.
    """
    totals = [0 for date in date_headers]
    rows = []
    for thing, thing_entries in groupby(entries, lambda x: x[by]):
        name, thing_id, date_dict = date_totals(thing_entries, by)
        dates = []
        for index, day in enumerate(date_headers):
            if isinstance(day, datetime.datetime):
                day = day.date()
            if hour_type:
                total = date_dict.get(day, {}).get(hour_type, 0)
                dates.append(total)
            else:
                billable = date_dict.get(day, {}).get('billable', 0)
                nonbillable = date_dict.get(day, {}).get('non_billable', 0)
                total = billable + nonbillable
                dates.append({
                    'day': day,
                    'billable': billable,
                    'nonbillable': nonbillable,
                    'total': total
                })
            totals[index] += total
        if total_column:
            dates.append(sum(dates))
        if overtime:
            dates.append(find_overtime(dates))
        dates = [date or '' for date in dates]
        rows.append((name, thing_id, dates))
    if total_column:
        totals.append(sum(totals))
    totals = [total or '' for total in totals]
    yield (rows, totals)


def payroll_totals(month_work_entries, month_leave_entries):
    """Summarizes monthly work and leave totals, grouped by user.

    Returns (labels, rows).
        labels -> {'billable': [proj_labels], 'nonbillable': [proj_labels]}
        rows -> [{
            name: name of user,
            billable, nonbillable, leave: [
                {'hours': hours for label, 'percent': % of work or leave total}
            ],
            work_total: sum of billable and nonbillable hours,
            leave_total: sum of leave hours
            grand_total: sum of work_total and leave_total
        }]

    The last entry in each of the billable/nonbillable/leave lists contains a
    summary of the status. The last row contains sum totals for all other rows.
    """
    def _get_user_info(entries):
        """Helper for getting the associated user's first and last name."""
        fname = entries[0].get('user__first_name', '') if entries else ''
        lname = entries[0].get('user__last_name', '') if entries else ''
        name = '{0} {1}'.format(fname, lname).strip()
        user_id = entries[0].get('user', None) if entries else None
        return {'name': name, 'user_id': user_id}

    def _get_index(status, label):
        """
        Returns the index in row[status] (where row is the row corresponding
        to the current user) where hours for the project label should be
        recorded.

        If the label does not exist, then it is added to the labels list.
        Each row and the totals row is updated accordingly.

        Requires that labels, rows, and totals are in scope.
        """
        if label in labels[status]:
            return labels[status].index(label)
        # Otherwise: update labels, rows, and totals to reflect the addition.
        labels[status].append(label)
        for row in rows:
            row[status].insert(-1, {'hours': Decimal(), 'percent': Decimal()})
        totals[status].insert(-1, {'hours': Decimal(), 'percent': Decimal()})
        return len(labels[status]) - 1

    def _construct_row(name, user_id=None):
        """Constructs an empty row for the given name."""
        row = {'name': name, 'user_id': user_id}
        for status in labels.keys():
            # Include an extra entry for summary.
            row[status] = [{'hours': Decimal(), 'percent': Decimal()}
                    for i in range(len(labels[status]) + 1)]
        row['work_total'] = Decimal()
        row['grand_total'] = Decimal()
        return row

    def _add_percentages(row, statuses, total):
        """For each entry in each status, percent = hours / total"""
        if total:
            for status in statuses:
                for i in range(len(row[status])):
                    p = row[status][i]['hours'] / total * 100
                    row[status][i]['percent'] = p

    def _get_sum(row, statuses):
        """Sum the number of hours worked in given statuses."""
        return sum([row[status][-1]['hours'] for status in statuses])

    work_statuses = ('billable', 'nonbillable')
    leave_statuses = ('leave', )
    labels = dict([(status, []) for status in work_statuses + leave_statuses])
    rows = []
    totals = _construct_row('Totals')
    for user, work_entries in groupby(month_work_entries, lambda e: e['user']):

        work_entries = list(work_entries)
        row = _construct_row(**_get_user_info(work_entries))
        rows.append(row)
        for entry in work_entries:
            status = 'billable' if entry['billable'] else 'nonbillable'
            label = entry['project__type__label']
            index = _get_index(status, label)
            hours = entry['hours']
            row[status][index]['hours'] += hours
            row[status][-1]['hours'] += hours
            totals[status][index]['hours'] += hours
            totals[status][-1]['hours'] += hours

        leave_entries = month_leave_entries.filter(user=user)
        status = 'leave'
        for entry in leave_entries:
            label = entry.get('project__name')
            index = _get_index(status, label)
            hours = entry.get('hours')
            row[status][index]['hours'] += hours
            row[status][-1]['hours'] += hours
            totals[status][index]['hours'] += hours
            totals[status][-1]['hours'] += hours

        row['work_total'] = _get_sum(row, work_statuses)
        _add_percentages(row, work_statuses, row['work_total'])
        row['leave_total'] = _get_sum(row, leave_statuses)
        _add_percentages(row, leave_statuses, row['leave_total'])
        row['grand_total'] = row['work_total'] + row['leave_total']

    totals['work_total'] = _get_sum(totals, work_statuses)
    _add_percentages(totals, work_statuses, totals['work_total'])
    totals['leave_total'] = _get_sum(totals, leave_statuses)
    _add_percentages(totals, leave_statuses, totals['leave_total'])
    totals['grand_total'] = totals['work_total'] + totals['leave_total']

    if rows:
        rows.append(totals)
    return labels, rows


def get_total_seconds(td):
    """
    The equivalent for datetime.timedelta.total_seconds() for Python 2.6
    """
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


def get_hours_per_week(user):
    """Retrieves the number of hours the user should work per week."""
    UserProfile = get_model('timepiece', 'UserProfile')
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
    Project = get_model('timepiece', 'Project')
    ScheduleAssignment = get_model('timepiece', 'ScheduleAssignment')

    # Determine all projects either worked or assigned.
    project_q = Q(id__in=assignments.values_list('project__id', flat=True))
    project_q |= Q(id__in=entries.values_list('project__id', flat=True))
    projects = Project.objects.filter(project_q).select_related('business')

    # Hours per project.
    project_data = {}
    for project in projects:
        try:
            assigned = assignments.get(project__id=project.pk).hours
        except ScheduleAssignment.DoesNotExist:
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
    Entry = get_model('timepiece', 'Entry')
    try:
        entry = Entry.no_join.get(user=user, end_time__isnull=True)
    except Entry.DoesNotExist:
        entry = None
    except Entry.MultipleObjectsReturned:
        raise ActiveEntryError('Only one active entry is allowed.')
    return entry
