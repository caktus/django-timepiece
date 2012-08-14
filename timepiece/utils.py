import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import time

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.db.models import Sum, get_model
from django.utils.functional import lazy
from django.core.urlresolvers import reverse

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone


reverse_lazy = lazy(reverse, str)


def slugify_uniquely(s, queryset=None, field='slug'):
    """
    Returns a slug based on 's' that is unique for all instances of the given
    field in the given queryset.

    If no string is given or the given string contains no slugify-able
    characters, default to the given field name + N where N is the number of
    default slugs already in the database.
    """
    new_slug = new_slug_base = slugify(s)
    if queryset:
        queryset = queryset.filter(**{'%s__startswith' % field: new_slug_base})
        similar_slugs = [value[0] for value in queryset.values_list(field)]
        i = 1
        while new_slug in similar_slugs:
            new_slug = "%s%d" % (new_slug_base, i)
            i += 1
    return new_slug


def render_with(template_name):
    """
    Renders the view wrapped by this decorator with the given template.  The
    view should return the context to be used in the template, or an
    HttpResponse.

    If the view returns an HttpResponseRedirect, the decorator will redirect
    to the given URL, or to request.REQUEST['next'] (if it exists).
    """
    def render_with_decorator(view_func):
        def wrapper(*args, **kwargs):
            request = args[0]
            response = view_func(*args, **kwargs)

            if isinstance(response, HttpResponse):
                if isinstance(response, HttpResponseRedirect) and \
                  'next' in request.REQUEST:
                    return HttpResponseRedirect(request.REQUEST['next'])
                else:
                    return response
            else:
                # assume response is a context dictionary
                context = response
                return render_to_response(
                    template_name,
                    context,
                    context_instance=RequestContext(request),
                )
        return wrapper
    return render_with_decorator


DEFAULT_TIME_FORMATS = [
    '%H:%M',        # 23:15         => 23:15:00
    '%H:%M:%S',     # 05:50:21      => 05:50:21
    '%I:%M:%S %p',  # 11:40:53 PM   => 23:40:53
    '%I:%M %p',     # 6:21 AM       => 06:21:00
    '%I %p',        # 1 pm          => 13:00:00
    '%I:%M:%S%p',   # 8:45:52pm     => 23:45:52
    '%I:%M%p',      # 12:03am       => 00:03:00
    '%I%p',         # 12pm          => 12:00:00
    '%H',           # 22            => 22:00:00
]


def add_timezone(value, tz=None):
    """If the value is naive, then the timezone is added to it.  

    If no timezone is given, timezone.get_current_timezone() is used.
    """   
    if tz == None:
        tz = timezone.get_current_timezone()
    try:
        if timezone.is_naive(value):
            return timezone.make_aware(value, tz)
    except AttributeError:  # 'datetime.date' object has no attribute 'tzinfo'
        dt = datetime.datetime.combine(value, datetime.time())
        return timezone.make_aware(dt, tz)
    return value


def parse_time(time_str, input_formats=None):
    """
    This function will take a string with some sort of representation of time
    in it.  The string will be parsed using a variety of formats until a match
    is found for the format given.  The return value is a datetime.time object.
    """
    formats = input_formats or DEFAULT_TIME_FORMATS

    # iterate over all formats until we find a match
    for format in formats:
        try:
            # attempt to parse the time with the current format
            value = time.strptime(time_str, format)
        except ValueError:
            continue
        else:
            # turn the time_struct into a datetime.time object
            return add_timezone(datetime.time(*value[3:6]))

    # return None if there's no matching format
    return None


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


def get_week_window(day):
    start = get_week_start(day)
    end = start + datetime.timedelta(weeks=1)
    weeks = generate_dates(end=end, start=start, by='week')
    return list(weeks)


def date_filter(func):
    def inner_decorator(request, *args, **kwargs):
        from timepiece import forms as timepiece_forms
        if 'to_date' in request.GET:
            form = timepiece_forms.DateForm(request.GET)
            if form.is_valid():
                from_date, to_date = form.save()
                status = form.cleaned_data.get('status')
                activity = form.cleaned_data.get('activity')
            else:
                raise Http404
        else:
            form = timepiece_forms.DateForm()
            today = datetime.date.today()
            from_date = today.replace(day=1)
            to_date = from_date + relativedelta(months=1)
            status = activity = None
        return func(request, form, from_date, to_date, status, activity,
            *args, **kwargs)
    return inner_decorator


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


def user_date_totals(user_entries):
    """Yield a user's name and a dictionary of their hours"""
    date_dict = {}
    for date, date_entries in groupby(user_entries, lambda x: x['date']):
        if isinstance(date, datetime.datetime):
            date = date.date()
        d_entries = list(date_entries)
        name = ' '.join((d_entries[0]['user__first_name'],
                        d_entries[0]['user__last_name']))
        hours = get_hours(d_entries)
        date_dict[date] = hours
    return name, date_dict


def project_totals(entries, date_headers, hour_type=None, overtime=False,
                   total_column=False):
    """
    Yield hour totals grouped by user and date. Optionally including overtime.
    """
    totals = [0 for date in date_headers]
    rows = []
    for user, user_entries in groupby(entries, lambda x: x['user']):
        name, date_dict = user_date_totals(user_entries)
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
        rows.append((name, dates))
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
    def _get_name(entries):
        """Helper for getting the associated user's first and last name."""
        fname = entries[0].get('user__first_name', '') if entries else ''
        lname = entries[0].get('user__last_name', '') if entries else ''
        name = '{0} {1}'.format(fname, lname).strip()
        return name

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

    def _construct_row(name):
        """Constructs an empty row for the given name."""
        row = {'name': name}
        for status in labels.keys():
            # Include an extra entry for summary.
            row[status] = [{'hours': Decimal(), 'percent': Decimal()}
                    for i in range(len(labels[status])+1)]
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
        row = _construct_row(_get_name(work_entries))
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


def get_project_hours_for_week(week_start):
    """
    Gets all ProjectHours entries in the 7-day period beginning on week_start.

    Returns a values set, ordered by the project id.
    """
    week_end = week_start + relativedelta(days=7)
    ProjectHours = get_model('timepiece', 'ProjectHours')
    qs = ProjectHours.objects.filter(week_start__gte=week_start,
            week_start__lt=week_end)
    qs = qs.values('project__id', 'project__name', 'user__id',
            'user__first_name', 'user__last_name', 'hours')
    qs = qs.order_by('-project__type__billable', 'project__name',)
    return qs


def get_people_from_project_hours(project_hours):
    """
    Gets a list of the distinct people included in the project hours entries,
    ordered by name.
    """
    people = project_hours.values_list('user__id', 'user__first_name',
            'user__last_name').distinct().order_by('user__first_name',
            'user__last_name')
    return people


def process_dates(dates, start=None, end=None):
    """
    A helper function to grab date strings from a dictionary
    or set detaults
    """
    from_date = dates.get('from_date', None)
    to_date = dates.get('to_date', None)

    from_date = datetime.datetime.strptime(from_date, '%m/%d/%Y') \
        if from_date else start
    to_date = datetime.datetime.strptime(to_date, '%m/%d/%Y') \
        if to_date else end

    return from_date, to_date


def process_todays_entries(entries):
    now = timezone.now().replace(microsecond=0)
    last_end = None
    if entries:
        start_time = entries[0].start_time
        last_end = entries[entries.count() - 1].end_time
    else:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = last_end if last_end is not None else now

    def get_entry_details(entry):
        entry.end_time = entry.end_time if entry.end_time else now
        return {
            'project': entry.project.name,
            'pk': entry.pk,
            'start_time': entry.start_time.isoformat(),
            'end_time': entry.end_time.isoformat(),
            'update_url': reverse('timepiece-update', args=(entry.pk,)),
            'hours': '%.2f' % round(entry.total_hours, 2),
        }
    return {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'entries': map(get_entry_details, entries),
    }


def get_total_seconds(td):
    """
    The equivalent for datetime.timedelta.total_seconds() for Python 2.6
    """
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


def get_active_hours(entry):
    """Use with active entries to obtain the time worked so far."""
    if not entry.end_time:
        if entry.is_paused:
            entry.end_time = entry.pause_time
        else:
            entry.end_time = timezone.now()
    return Decimal('%.2f' % round(entry.total_hours, 2))


def process_weeks_entries(user, week_start, entries):
    """Summarizes the user's hours over the provided week's entries.

    Returns a dictionary containing a summary of hours worked:
    {
        'worked': 123.45,
        'remaining': 123.45,
        'projects': [
            {
                'pk': 123,
                'name': 'abc',
                'worked': 123.45,
                'remaining': 123.45,
            }
        ],
    }
    """

    def _initialize_in_projects(entry):
        """
        Helper method which adds new project record to projects if there is 
        no record for the project associated with this entry.

        Requires projects, proj_hours, and ProjectHours in scope.
        """
        if entry.project_id not in projects:
            try:
                remaining = proj_hours.get(project=entry.project).hours
            except ProjectHours.DoesNotExist:
                remaining = None
            projects[entry.project.pk] = {
                'pk': entry.project.pk,
                'name': entry.project.name,
                'worked': Decimal('0.00'),
                'remaining': remaining,
            }

    ProjectHours = get_model('timepiece', 'ProjectHours')
    proj_hours = ProjectHours.objects.filter(user=user, week_start=week_start)
    PersonSchedule = get_model('timepiece', 'PersonSchedule')
    try:
        sched = PersonSchedule.objects.get(user=user)
    except PersonSchedule.DoesNotExist:
        sched = None
    total_hours = sched.hours_per_week if sched else Decimal('40.00')
    
    all_worked = Decimal('0.00')
    all_remaining = total_hours
    projects = {}  # Worked/remaining hours per project
    for entry in entries:
        _initialize_in_projects(entry)
        pk = entry.project_id
        hours = get_active_hours(entry)
        all_worked += hours
        projects[pk]['worked'] = projects[pk]['worked'] + hours
        all_remaining -= hours
        if projects[pk]['remaining']:
            projects[pk]['remaining'] = projects[pk]['remaining'] - hours

    # Convert Decimals to string so they can be serialized.
    total_hours = '%.2f' % round(total_hours, 2)
    all_worked = '%.2f' % round(all_worked, 2)
    all_remaining = '%.2f' % round(all_remaining, 2)
    for project in projects.values():
        project['worked'] = '%.2f' % round(project['worked'], 2)
        if project['remaining'] is not None:
            project['remaining'] = '%.2f' % round(project['remaining'], 2)
        
    return {
        'total_hours': total_hours,
        'worked': all_worked,
        'remaining': all_remaining,
        'projects': projects.values(),
    }
