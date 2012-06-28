from datetime import date as date_obj, datetime, timedelta, time as time_obj
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import time
import calendar

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.db.models import Sum
from django.contrib.sites.models import Site
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
            return timezone.make_aware(time_obj(*value[3:6]),
                timezone.get_current_timezone())

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
        from_day = date_obj.today()
    from_day = datetime.combine(from_day,
        time_obj(tzinfo=timezone.get_current_timezone()))
    return from_day.replace(day=1)


def get_week_start(day=None):
    if not day:
        day = date_obj.today()
    isoweekday = day.isoweekday()
    if isoweekday != 1:
        day = day - timedelta(days=isoweekday - 1)
    day = datetime.combine(day,
        time_obj(tzinfo=timezone.get_current_timezone()))
    return day


def get_last_billable_day(day=None):
    if not day:
        day = date_obj.today()
    day += relativedelta(months=1)
    return get_week_start(get_month_start(day)) - timedelta(days=1)


def generate_dates(start=None, end=None, by='week'):
    try:
        if not timezone.is_aware(start):
            start = timezone.make_aware(start, timezone.get_current_timezone())
    except AttributeError:
        if start:
            start = datetime.combine(start,
                time_obj(tzinfo=timezone.get_current_timezone()))
    try:
        if not timezone.is_aware(end):
            end = timezone.make_aware(end, timezone.get_current_timezone())
    except AttributeError:
        if end:
            end = datetime.combine(end,
                time_obj(tzinfo=timezone.get_current_timezone()))
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
    end = start + timedelta(weeks=1)
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
            today = date_obj.today()
            from_date = today.replace(day=1)
            to_date = from_date + relativedelta(months=1)
            status = activity = None
        return func(request, form, from_date, to_date, status, activity,
            *args, **kwargs)
    return inner_decorator


def get_hours(entries):
    hours = {'total': 0}
    for entry in entries:
        hours['total'] += entry['hours']
        if entry['billable']:
            hours['billable'] = entry['hours']
        else:
            hours['non_billable'] = entry['hours']
    return hours


def daily_summary(day_entries):
    projects = {}
    all_day = {}
    for name, entries in groupby(day_entries,
                                           lambda x: x['project__name']):
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
        try:
            if timezone.is_naive(week):
                week = timezone.make_aware(week,
                    timezone.get_current_timezone())
        except AttributeError:
            week = datetime.combine(week,
                timezone.get_current_timezone())
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


def format_leave(leave):
    """
    Formats leave time to ([(project name, hours)], total hours)
    """
    leave_hours = 0
    leave_desc = {}
    for entry in leave:
        pj = entry.get('project__name')
        pj_hours = entry.get('hours')
        old = leave_desc.get(pj, 0)
        leave_desc[pj] = pj_hours + old
        leave_hours += pj_hours
    return leave_desc.items(), leave_hours


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
        if isinstance(date, datetime):
            date = date.date()
        d_entries = list(date_entries)
        name = ' '.join((d_entries[0]['user__first_name'],
                        d_entries[0]['user__last_name']))
        hours = get_hours(d_entries)
        date_dict[date] = hours
    return name, date_dict


def project_totals(entries, date_headers, hour_type, overtime=False,
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
            if isinstance(day, datetime):
                day = day.date()
            total = date_dict.get(day, {}).get(hour_type, 0)
            totals[index] += total
            dates.append(total)
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


def payroll_totals(entries, date, leave):
    """
    Yield totals for a month, grouped by user and billable status of each entry
    """
    all_leave_hours = {}
    all_paid_hours = 0
    all_worked_hours = [0, 0, 0]

    def construct_all_worked_hours(hours_dict, leave_hours):
        """Helper for summing the worked hours list for all users"""
        billable = hours_dict.get('billable', 0)
        non_billable = hours_dict.get('non_billable', 0)
        total_worked = hours_dict.get('total', 0)
        worked_hours = [billable, non_billable, total_worked]
        return map(sum, zip(worked_hours, all_worked_hours))

    date = date_obj(month=date.month, day=date.day, year=date.year)
    for user, user_entries in groupby(entries, lambda x: x['user']):
        name, date_dict = user_date_totals(user_entries)
        hours_dict = date_dict.get(date, {})
        worked_hours = get_hour_summaries(hours_dict)
        leave_desc, leave_hours = format_leave(leave.filter(user=user))
        paid_hours = worked_hours[2] + leave_hours
        # Add totals for all users
        all_worked_hours = construct_all_worked_hours(hours_dict, leave_hours)
        for desc, hours in leave_desc:
            all_leave_hours[desc] = all_leave_hours.get(desc, 0) + hours
        all_paid_hours += paid_hours
        yield (name, worked_hours, leave_desc, paid_hours)
    nested_hours = get_hour_summaries(all_worked_hours)
    if all_paid_hours:
        yield ('Totals', nested_hours, all_leave_hours.items(), all_paid_hours)
