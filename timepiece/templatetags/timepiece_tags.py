import datetime

from collections import OrderedDict
from dateutil.relativedelta import relativedelta

from six.moves.urllib.parse import urlencode

from django import template
from django.urls import reverse
from django.db.models import Sum
from django.template.defaultfilters import date as date_format_filter
from django.utils.safestring import mark_safe

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT


register = template.Library()


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
        return '{0}{1}{2}'.format(url, sep, urlencode(parameters))
    return url


@register.filter
def add_timezone(date, tz=None):
    """Return the given date with timezone added."""
    return utils.add_timezone(date, tz)


@register.simple_tag
def create_dict(**kwargs):
    """Utility to create a dictionary from keyword arguments."""
    return kwargs


@register.inclusion_tag('timepiece/date_filters.html')
def date_filters(form_id, options=None, use_range=True):
    if not options:
        options = ('months', 'quarters', 'years')
    filters = OrderedDict()
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

    return {'filters': filters, 'form_id': form_id}


@register.simple_tag(takes_context=True)
def get_max_hours(context):
    """Return the largest number of hours worked or assigned on any project."""
    progress = context['project_progress']
    return max([0] + [max(p['worked'], p['assigned']) for p in progress])


@register.simple_tag
def get_uninvoiced_hours(entries, billable=None):
    """Given an iterable of entries, return the total hours that have
    not been invoiced. If billable is passed as 'billable' or 'nonbillable',
    limit to the corresponding entries.
    """
    statuses = ('invoiced', 'not-invoiced')
    if billable is not None:
        billable = (billable.lower() == u'billable')
        entries = [e for e in entries if e.activity.billable == billable]
    hours = sum([e.hours for e in entries if e.status not in statuses])
    return '{0:.2f}'.format(hours)


@register.filter
def humanize_hours(total_hours, frmt='{hours:02d}:{minutes:02d}:{seconds:02d}',
                   negative_frmt=None):
    """Given time in hours, return a string representing the time."""
    seconds = int(float(total_hours) * 3600)
    return humanize_seconds(seconds, frmt, negative_frmt)


@register.filter
def humanize_seconds(total_seconds,
                     frmt='{hours:02d}:{minutes:02d}:{seconds:02d}',
                     negative_frmt=None):
    """Given time in int(seconds), return a string representing the time.

    If negative_frmt is not given, a negative sign is prepended to frmt
    and the result is wrapped in a <span> with the "negative-time" class.
    """
    if negative_frmt is None:
        negative_frmt = '<span class="negative-time">-{0}</span>'.format(frmt)
    seconds = abs(int(total_seconds))
    mapping = {
        'hours': seconds // 3600,
        'minutes': seconds % 3600 // 60,
        'seconds': seconds % 3600 % 60,
    }
    if total_seconds < 0:
        result = negative_frmt.format(**mapping)
    else:
        result = frmt.format(**mapping)
    return mark_safe(result)


@register.filter
def multiply(a, b):
    """Return a * b."""
    return float(a) * float(b)


@register.simple_tag
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


def _project_report_url_params(contract, project):
    return {
        'from_date': contract.start_date.strftime(DATE_FORM_FORMAT),
        'to_date': contract.end_date.strftime(DATE_FORM_FORMAT),
        'billable': 1,
        'non_billable': 0,
        'paid_leave': 0,
        'trunc': 'month',
        'projects_1': project.id,
    }


@register.simple_tag
def project_report_url_for_contract(contract, project):
    data = _project_report_url_params(contract, project)
    return '{0}?{1}'.format(reverse('report_hourly'), urlencode(data))


@register.simple_tag
def project_timesheet_url(project_id, date=None):
    """Shortcut to create a time sheet URL with optional date parameters."""
    return _timesheet_url('view_project_timesheet', project_id, date)


@register.filter
def seconds_to_hours(seconds):
    """Given time in int seconds, return decimal seconds."""
    return round(seconds / 3600.0, 2)


@register.simple_tag
def sum_hours(entries):
    """Return the sum total of get_total_seconds() for each entry."""
    return sum([e.get_total_seconds() for e in entries])


def _timesheet_url(url_name, pk, date=None):
    """Utility to create a time sheet URL with optional date parameters."""
    url = reverse(url_name, args=(pk,))
    if date:
        params = {'month': date.month, 'year': date.year}
        return '?'.join((url, urlencode(params)))
    return url


@register.simple_tag
def user_timesheet_url(user_id, date=None):
    """Shortcut to create a time sheet URL with optional date parameters."""
    return _timesheet_url('view_user_timesheet', user_id, date)


@register.filter
def week_start(date):
    """Return the starting day of the week with the given date."""
    return utils.get_week_start(date)
