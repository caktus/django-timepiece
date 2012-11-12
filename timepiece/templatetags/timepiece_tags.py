import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from dateutil import rrule
import urllib

from django import template
from django.core.urlresolvers import reverse

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import utils


register = template.Library()


@register.filter
def multiply(a, b):
    return float(a) * float(b)


@register.filter
def seconds_to_hours(seconds):
    return round(seconds / 3600.0, 2)


@register.inclusion_tag('timepiece/time-sheet/_date_filters.html')
def date_filters(form_id, options=None, use_range=True):
    if not options:
        options = ('months', 'quarters', 'years')
    filters = {}
    date_format = '%m/%d/%Y'
    today = datetime.date.today()
    single_day = relativedelta(days=1)
    single_month = relativedelta(months=1)
    single_year = relativedelta(years=1)

    if 'months' in options:
        filters['Past 12 Months'] = []
        from_date = today.replace(day=1) + single_month
        for x in range(12):
            to_date = from_date
            from_date = to_date - single_month
            to_date = to_date - single_day
            filters['Past 12 Months'].append((
                    from_date.strftime("%b '%y"),
                    from_date.strftime(date_format) if use_range else "",
                    to_date.strftime(date_format)
            ))
        filters['Past 12 Months'].reverse()

    if 'years' in options:
        filters['Years'] = []
        start = today.year - 3
        for year in range(start, start + 4):
            from_date = datetime.datetime(year, 1, 1)
            to_date = from_date + single_year - single_day
            filters['Years'].append((
                    str(from_date.year),
                    from_date.strftime(date_format) if use_range else "",
                    to_date.strftime(date_format)
            ))

    if 'quarters' in options:
        filters['Quarters (Calendar Year)'] = []
        to_date = datetime.date(today.year - 1, 1, 1) - single_day
        for x in range(8):
            from_date = to_date + single_day
            to_date = from_date + relativedelta(months=3) - single_day
            filters['Quarters (Calendar Year)'].append((
                    'Q%s %s' % ((x % 4) + 1, from_date.year),
                    from_date.strftime(date_format) if use_range else "",
                    to_date.strftime(date_format)
            ))

    return {'filters': filters, 'form_id': form_id}


@register.inclusion_tag('timepiece/time-sheet/invoice/_invoice_subheader.html',
                        takes_context=True)
def invoice_subheaders(context, current):
    return {
        'current': current,
        'invoice': context['invoice'],
    }


@register.simple_tag
def week_start(date):
    return utils.get_week_start(date).strftime('%m/%d/%Y')


@register.simple_tag
def get_uninvoiced_hours(entries):
    hours_uninvoiced = 0
    for entry in entries:
        if entry['status'] != 'invoiced' and entry['status'] != 'not-invoiced':
            hours_uninvoiced += entry['s']
    return hours_uninvoiced


@register.filter
def humanize_hours(total_hours):
    """Given time in Decimal(hours), return a unicode in %H:%M:%S format."""
    return humanize_seconds(float(total_hours) * 3600)


@register.filter
def humanize_seconds(total_seconds):
    """Given time in int(seconds), return a unicode in %H:%M:%S format."""
    seconds = abs(int(total_seconds))
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    prefix = u'-' if total_seconds < 0 else u''
    return prefix + reduce(lambda a, b: u':'.join((a, b)),
        map(lambda u: unicode(u) if u > 9 else u'0' + unicode(u),
            (hours, minutes, seconds)
        )
    )


@register.filter
def work_days(end):
    weekdays = (rrule.MO, rrule.TU, rrule.WE, rrule.TH, rrule.FR)
    days = rrule.rrule(rrule.DAILY, byweekday=weekdays,
                       dtstart=datetime.date.today(), until=end)
    return len(list(days))


@register.simple_tag
def timesheet_url(type, pk, date):
    if type == 'project':
        name = 'project_time_sheet'
    elif type == 'user':
        name = 'view_person_time_sheet'

    url = reverse(name, args=(pk,))
    params = {'month': date.month, 'year': date.year} if date else {}

    return '?'.join((url, urllib.urlencode(params),))
