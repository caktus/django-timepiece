import datetime
from dateutil.relativedelta import relativedelta
import urllib

from django import template
from django.core.urlresolvers import reverse
from django.db.models import Sum

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import utils


register = template.Library()


# This is a good candidate for an assignment_tag, once we no longer
# have to support Django 1.3.
@register.simple_tag(takes_context=True)
def sum_hours(context, entries, variable='daily_total'):
    context[variable] = sum([e.get_total_seconds() for e in entries])
    return ''


@register.filter
def multiply(a, b):
    return float(a) * float(b)


@register.filter
def seconds_to_hours(seconds):
    return round(seconds / 3600.0, 2)


@register.inclusion_tag('timepiece/date_filters.html')
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


@register.simple_tag
def week_start(date):
    """Given a Python date/datetime object, return the starting day of that
    week in "mm/dd/yyyy" format.
    """
    return utils.get_week_start(date).strftime('%m/%d/%Y')


@register.simple_tag
def get_uninvoiced_hours(entries):
    statuses = ('invoiced', 'not-invoiced')
    hours = sum([e.hours for e in entries if e.status not in statuses])
    return hours


@register.filter
def convert_hours_to_seconds(total_hours):
    """Given time in Decimal(hours), return a unicode in %H:%M:%S format."""
    return int(float(total_hours) * 3600)


@register.filter
def humanize_seconds(total_seconds, format='%H:%M:%S'):
    """Given time in int(seconds), return a unicode in %H:%M:%S format."""
    seconds = abs(int(total_seconds))
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    format_mapping = {
        '%H': hours,
        '%M': minutes,
        '%S': seconds,
    }
    time_units = [
        format_mapping[token] for token in format.split(':')
        if token in format_mapping
    ]
    result = ':'.join([
        u'{0:02d}'.format(time_unit) for time_unit in time_units
    ])
    return result if total_seconds >= 0 else '({0})'.format(result)


@register.simple_tag
def timesheet_url(type, pk, date):
    if type == 'project':
        name = 'view_project_timesheet'
    elif type == 'user':
        name = 'view_user_timesheet'

    url = reverse(name, args=(pk,))
    params = {'month': date.month, 'year': date.year} if date else {}

    return '?'.join((url, urllib.urlencode(params),))


@register.simple_tag(takes_context=True)
def get_max_hours(context):
    """
    Returns the largest number of hours worked or assigned on any project.
    """
    project_progress = context['project_progress']
    max_hours = 0
    for project in project_progress:
        max_hours = max(max_hours, project['worked'], project['assigned'])
    return str(max_hours)


# This is a good candidate for an assignment_tag, once we no longer
# have to support Django 1.3.
@register.simple_tag(takes_context=True)
def project_hours_for_contract(context, contract, project,
        variable='project_hours'):
    """Total hours worked on project for contract."""
    hours = contract.entries.filter(project=project)\
                           .aggregate(s=Sum('hours'))['s'] or 0
    context[variable] = hours
    return ''


@register.simple_tag
def project_report_url_for_contract(contract, project):
    data = {
        'from_date': contract.start_date.strftime('%m/%d/%Y'),
        'to_date': contract.end_date.strftime('%m/%d/%Y'),
        'billable': 1,
        'non_billable': 1,
        'paid_leave': 1,
        'trunc': 'month',
        'projects_1': project.id,
    }
    return '{0}?{1}'.format(reverse('report_hourly'), urllib.urlencode(data))
