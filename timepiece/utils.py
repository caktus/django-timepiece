from datetime import date, datetime, timedelta, time as time_obj
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import itertools
import time
import calendar

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.db.models import Sum
from django.contrib.sites.models import Site


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


def determine_period(the_date=date.today(), delta=0):
    """
    Determine the start and end date for an accounting period.  If a date
    is passed in, that date will be used to determine the accounting period.
    If no date is passed in, the current date will be used.
    """
    delta = int(delta)

    try:
        # attempt to get the configuration for the current site
        site = Site.objects.get_current()
        config = site.timepiececonfiguration
    except:
        raise Exception('Please configure Pendulum for %s!' % site)

    if config.is_monthly and (config.month_start >= 1 \
    and config.month_start <= 31):
        if config.month_start == 1:
            #if the periods start on the first of the month, just use the first
            #and last days of each month for the period
            if delta > 0:
                diff = the_date.month - delta
                if diff < 1:
                    # determine how many years to go back
                    years = abs(diff / 12)

                    # determine how many months to go back
                    months = delta - (years * 12)
                    if months == the_date.month:
                        # don't give an invalid month
                        months = -1
                        years += 1

                    # now set the year and month
                    year = the_date.year - years
                    month = the_date.month - months
                else:
                    year, month = the_date.year, diff
            else:
                year, month = the_date.year, the_date.month

            num_days = calendar.monthrange(year, month)[1]
            sy, sm, sd = year, month, 1
            ey, em, ed = year, month, num_days
        else:
            # if the periods don't start on the first of the month, try to
            # figure out which days are required

            sy, sm, sd = the_date.year, the_date.month, config.month_start

            # now take the delta into account
            if delta > 0:
                diff = sm - delta
                if diff < 1:
                    # determine how many years to go back
                    years = abs(diff / 12)

                    # determine how many months to go back
                    months = delta - (years * 12)
                    if months == sm:
                        # don't give an invalid month
                        months = -1
                        years += 1

                    # now set the year and month
                    sy, sm = sy - years, sm - months
                else:
                    sm = diff

            if the_date.day >= config.month_start:
                # if we are already into the period that began this month
                if sm == 12:
                    # see if the period spans into the next year
                    ey, em = sy + 1, 1
                else:
                    # if not, just add a month and subtract a day
                    ey, em = sy, em + 1
            else:
                # if we are in the period that ends this month
                if sm == 1:
                    # and we're in January, set the start to last december
                    sy, sm = sy - 1, 12
                    ey, em = sy + 1, 1
                else:
                    # otherwise, just keep it simple
                    sm = sm - 1
                    ey, em = sy, sm + 1

            ed = sd - 1

            # this should handle funky situations where a period begins on the
            # 31st of a month or whatever...
            num_days = calendar.monthrange(ey, em)[1]
            if ed > num_days:
                ed = num_days

    elif config.install_date and config.period_length:
        #if we have periods with a set number of days...
        #find out how many days have passed since the installation date
        diff = the_date - config.install_date

        #find out how many days are left over after dividing the number of days
        #since installation by the length of the period
        days_into_period = diff.days % config.period_length

        #determine the start date of the period
        start = the_date - timedelta(days=days_into_period)

        #now take into account the delta
        if delta > 0:
            start = start - timedelta(days=(delta * config.period_length))
            end = start + timedelta(days=config.period_length - 1)
        else:
            #determine the end date of the period
            end = the_date + \
            timedelta(days=(config.period_length - days_into_period - 1))

        sy, sm, sd = start.year, start.month, start.day
        ey, em, ed = end.year, end.month, end.day
    else:
        raise Exception('Invalid Pendulum configuration for %s' % site)

    start_date = datetime(sy, sm, sd, 0, 0, 0)
    end_date = datetime(ey, em, ed, 23, 59, 59)

    return (start_date, end_date)

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
            return time_obj(*value[3:6])

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


def get_week_start(day=None):
    if not day:
        day = date.today()
    isoweekday = day.isoweekday()
    if isoweekday != 1:
        day = day - timedelta(days=isoweekday - 1)
    return day


def get_last_billable_day(day=None):
    if not day:
        day = date.today()
    day += relativedelta(months=1)
    return get_week_start(day) - timedelta(days=1)


def generate_weeks(end, start=None):
    start = get_week_start(start)
    #byweekday is set to Sunday, the last day of an ISO week
    return rrule.rrule(rrule.WEEKLY, dtstart=start, until=end, byweekday=0)


def get_week_window(day):
    start = get_week_start(day)
    end = start + timedelta(weeks=1)
    weeks = generate_weeks(start=start, end=end)
    return list(weeks)


def date_filter(func):
    def inner_decorator(request, *args, **kwargs):
        from timepiece import forms as timepiece_forms
        if request.GET:
            form = timepiece_forms.DateForm(request.GET)
            if form.is_valid():
                from_date, to_date = form.save()
                status = form.cleaned_data.get('status')
                activity = form.cleaned_data.get('activity')
            else:
                raise Http404
        else:
            form = timepiece_forms.DateForm()
            today = date.today()
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
    for name, entries in itertools.groupby(day_entries,
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
    daily = daily.annotate(hours=Sum('hours')).order_by('date', 'project__name')
    weeks = {}
    for week, week_entries in itertools.groupby(weekly, lambda x: x['date']):
        weeks[week] = get_hours(week_entries)
    days = []
    last_week = None
    for day, day_entries in itertools.groupby(daily, lambda x: x['date']):
        week = get_week_start(day)
        if last_week and week > last_week:
            yield last_week, weeks.get(last_week, {}), days
            days = []
        days.append((day, daily_summary(day_entries)))
        last_week = week
    yield week, weeks.get(week, {}), days
