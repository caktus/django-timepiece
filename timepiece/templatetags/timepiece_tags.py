import urllib
import datetime
import time
import calendar
from decimal import Decimal

from django import template
from django.db.models import Sum

from django.core.urlresolvers import reverse

from dateutil.relativedelta import relativedelta
from dateutil import rrule

from timepiece.models import PersonRepeatPeriod, AssignmentAllocation
import timepiece.models as timepiece
from timepiece.utils import get_total_time, get_week_start, get_month_start


register = template.Library()


@register.filter
def seconds_to_hours(seconds):
    return round(seconds / 3600.0, 2)


@register.inclusion_tag('timepiece/time-sheet/bar_graph.html',
                        takes_context=True)
def bar_graph(context, name, worked, total, width=None, suffix=None):
    if not width:
        width = 400
        suffix = 'px'
    left = total - worked
    over = 0
    over_total = 0
    error = ''
    if worked < 0:
        error = 'Somehow you\'ve logged %s negative hours for %s this week.' \
        % (abs(worked), name)
    if left < 0:
        over = abs(left)
        left = 0
        worked = total
        total = over + total
    return {
        'name': name, 'worked': worked,
        'total': total, 'left': left,
        'over': over, 'width': width,
        'suffix': suffix, 'error': error,
        }


@register.inclusion_tag('timepiece/time-sheet/my_ledger.html',
                        takes_context=True)
def my_ledger(context):
    try:
        period = PersonRepeatPeriod.objects.select_related(
            'user',
            'repeat_period',
        ).get(
            user=context['request'].user
        )
    except PersonRepeatPeriod.DoesNotExist:
        return {'period': False}
    return {'period': period}


@register.inclusion_tag('timepiece/time-sheet/_date_filters.html',
    takes_context=True)
def date_filters(context, options=None):
    request = context['request']
    from_slug = 'from_date'
    to_slug = 'to_date'
    use_range = True
    if not options:
        options = ('months', 'quarters', 'years')

    def construct_url(from_date, to_date):
        query = request.GET.copy()
        query.pop(to_slug, None)
        query.pop(from_slug, None)
        query[to_slug] = to_date.strftime('%m/%d/%Y')
        if use_range:
            query[from_slug] = from_date.strftime('%m/%d/%Y')
        return '%s?%s' % (request.path, query.urlencode())

    filters = {}
    if 'months_no_range' in options:
        filters['Past 12 Months'] = []
        single_month = relativedelta(months=1)
        from_date = datetime.date.today().replace(day=1) + \
            relativedelta(months=1)
        for x in range(12):
            to_date = from_date
            use_range = False
            from_date = to_date - single_month
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Past 12 Months'].append(
                (from_date.strftime("%b '%y"), url))
        filters['Past 12 Months'].reverse()

    if 'months' in options:
        filters['Past 12 Months'] = []
        single_month = relativedelta(months=1)
        from_date = datetime.date.today().replace(day=1) + \
            relativedelta(months=1)
        for x in range(12):
            to_date = from_date
            from_date = to_date - single_month
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Past 12 Months'].append(
                (from_date.strftime("%b '%y"), url))
        filters['Past 12 Months'].reverse()

    if 'years' in options:
        start = datetime.date.today().year - 3

        filters['Years'] = []
        for year in range(start, start + 4):
            from_date = datetime.datetime(year, 1, 1)
            to_date = from_date + relativedelta(years=1)
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Years'].append((str(from_date.year), url))

    if 'quarters' in options:
        filters['Quarters (Calendar Year)'] = []
        to_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        for x in range(8):
            from_date = to_date
            to_date = from_date + relativedelta(months=3)
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Quarters (Calendar Year)'].append(
                ('Q%s %s' % ((x % 4) + 1, from_date.year), url)
            )

    return {'filters': filters}


@register.inclusion_tag('timepiece/time-sheet/invoice/_invoice_subheader.html',
                        takes_context=True)
def invoice_subheaders(context, current):
    return {
        'current': current,
        'invoice': context['invoice'],
    }

@register.simple_tag
def hours_for_assignment(assignment, date):
    end = date + relativedelta(days=5)
    blocks = assignment.blocks.filter(
        date__gte=date, date__lte=end).select_related()
    hours = blocks.aggregate(hours=Sum('hours'))['hours']
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def total_allocated(assignment):
    hours = assignment.blocks.aggregate(hours=Sum('hours'))['hours']
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def hours_for_week(user, date):
    end = date + relativedelta(days=5)
    blocks = AssignmentAllocation.objects.filter(assignment__user=user,
                                                 date__gte=date, date__lte=end)
    hours = blocks.aggregate(hours=Sum('hours'))['hours']
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def weekly_hours_worked(rp, date):
    hours = rp.hours_in_week(date)
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def monthly_overtime(rp, date):
    hours = rp.total_monthly_overtime(date)
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def week_start(date):
    return get_week_start(date).strftime('%m/%d/%Y')


@register.simple_tag
def get_active_hours(entry):
    """Use with active entries to obtain time worked so far"""
    if not entry.end_time:
        if entry.is_paused:
            entry.end_time = entry.pause_time
        else:
            entry.end_time = datetime.datetime.now()
    return Decimal('%.2f' % round(entry.total_hours, 2))


@register.simple_tag
def show_cal(from_date, offset=0):
    date = get_month_start(from_date)
    date = date + relativedelta(months=offset)
    html_cal = calendar.HTMLCalendar(calendar.SUNDAY)
    return html_cal.formatmonth(date.year, date.month)


@register.simple_tag
def get_uninvoiced_hours(entries):
    hours_uninvoiced = 0
    for entry in entries:
        if entry['status'] != 'invoiced' and entry['status'] != 'not-invoiced':
            hours_uninvoiced += entry['s']
    return hours_uninvoiced


@register.filter
def work_days(end):
    weekdays = (rrule.MO, rrule.TU, rrule.WE, rrule.TH, rrule.FR)
    days = rrule.rrule(rrule.DAILY, byweekday=weekdays,
                       dtstart=datetime.date.today(), until=end)
    return len(list(days))
