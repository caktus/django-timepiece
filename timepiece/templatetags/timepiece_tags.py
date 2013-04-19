import datetime
from dateutil.relativedelta import relativedelta
import urllib

from django import template
from django.core.urlresolvers import reverse
from django.db.models import Sum
from django.template.defaultfilters import date as date_format_filter
from django.utils import timezone

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT


register = template.Library()


@register.assignment_tag
def sum_hours(entries):
    return sum([e.get_total_seconds() for e in entries])


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
    date_format = DATE_FORM_FORMAT  # Expected for dates used in code
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
                    date_format_filter(from_date, 'M Y'),  # displayed
                    from_date.strftime(date_format) if use_range else "",  # used in code
                    to_date.strftime(date_format)  # used in code
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
    week as a date object formatted by the |date filter.
    """
    return date_format_filter(utils.get_week_start(date))


@register.simple_tag
def get_uninvoiced_hours(entries, billable=None):
    """Given an iterable of entries, return the total hours that have
    not been invoices. If billable is passed as 'billable' or 'nonbillable',
    limit to the corresponding entries.
    """
    statuses = ('invoiced', 'not-invoiced')
    if billable is not None:
        billable = (billable.lower() == u'billable')
        entries = [e for e in entries if e.activity.billable == billable]
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


@register.assignment_tag
def project_hours_for_contract(contract, project, billable=None):
    """Total billable hours worked on project for contract.
    If billable is passed as 'billable' or 'nonbillable', limits to
    the corresponding hours.  (Must pass a variable name first, of course.)
    """
    hours = contract.entries.filter(project=project)
    if billable is not None:
        if billable in (u'billable', u'nonbillable'):
            billable = (billable.lower() == u'billable')
            hours = hours.filter(activity__billable=billable)
        else:
            msg = '`project_hours_for_contract` arg 4 must be "billable" ' \
                  'or "nonbillable"'
            raise template.TemplateSyntaxError(msg)
    hours = hours.aggregate(s=Sum('hours'))['s'] or 0
    return hours


@register.simple_tag
def project_report_url_for_contract(contract, project):
    data = {
        'from_date': contract.start_date.strftime(DATE_FORM_FORMAT),
        'to_date': contract.end_date.strftime(DATE_FORM_FORMAT),
        'billable': 1,
        'non_billable': 0,
        'paid_leave': 0,
        'trunc': 'month',
        'projects_1': project.id,
    }
    return '{0}?{1}'.format(reverse('report_hourly'), urllib.urlencode(data))


@register.filter
def add_parameters(url, parameters):
    """
    Appends URL-encoded parameters to the base URL. It appends after '&' if
    '?' is found in the URL; otherwise it appends using '?'. Keep in mind that
    this tag does not take into account the value of existing params; it is
    therefore possible to add another value for a pre-existing parameter.

    For example::

        {% url 'this_view' as current_url %}
        {% with complete_url=current_url|add_parameters:request.GET %}
            The <a href="{% url 'other' %}?next={{ complete_url|urlencode }}">
            other page</a> will redirect back to the current page (including
            any GET parameters).
        {% endwith %}
    """
    if parameters:
        sep = '&' if '?' in url else '?'
        return '{0}{1}{2}'.format(url, sep, urllib.urlencode(parameters))
    return url


@register.assignment_tag
def create_dict(**kwargs):
    """Utility to create a dictionary from arguments."""
    return kwargs


@register.filter
def add_timezone(date, tz=None):
    return utils.add_timezone(date, tz)
