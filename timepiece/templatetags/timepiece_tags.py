import datetime

from django import template
from django.db.models import Sum

from dateutil.relativedelta import relativedelta

from timepiece.models import PersonRepeatPeriod, ContractBlock


register = template.Library()


@register.filter
def seconds_to_hours(seconds):
    return round(seconds/3600.0, 2)


@register.inclusion_tag('timepiece/time-sheet/my_ledger.html',
                        takes_context=True)
def my_ledger(context):
    try:
        period = PersonRepeatPeriod.objects.get(contact__user = context['request'].user)
    except PersonRepeatPeriod.DoesNotExist:
        return { 'period': False }
    return { 'period': period }


@register.inclusion_tag('timepiece/time-sheet/_date_filters.html', takes_context=True)
def date_filters(context, options):
    request = context['request']
    from_slug = 'from_date'
    to_slug = 'to_date'
    use_range = True
    if not options:
        options = ('months', 'quaters', 'years')
    
    def construct_url(from_date, to_date):
        url = '%s?%s=%s' % (
            request.path,
            to_slug,
            to_date.strftime('%m/%d/%Y'),
        )
        if use_range:
            url += '&%s=%s' % (
                from_slug,
                from_date.strftime('%m/%d/%Y'),
            )
        return url

    filters = {}
    
    if 'months' in options:
        filters['Past 12 Months'] = []
        single_month = relativedelta(months=1)
        from_date = datetime.date.today().replace(day=1) + relativedelta(months=1)
        for x in range(12):
            to_date = from_date
            from_date = to_date - single_month
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Past 12 Months'].append((from_date.strftime("%b '%y"), url))
        filters['Past 12 Months'].reverse()
    
    if 'years' in options:
        start = datetime.date.today().year - 3
        
        filters['Years'] = []
        for year in range(start, start + 3):
            from_date = datetime.datetime(year, 1, 1)
            to_date = from_date + relativedelta(years=1)
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Years'].append((str(from_date.year), url))

    if 'quaters' in options:
        filters['Quaters (Calendar Year)'] = []
        to_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        for x in range(8):
            from_date = to_date
            to_date = from_date + relativedelta(months=3)
            url = construct_url(from_date, to_date - relativedelta(days=1))
            filters['Quaters (Calendar Year)'].append(
                ('Q%s %s' % ((x % 4) + 1, from_date.year), url)
            )

    return {'filters': filters}


@register.simple_tag
def hours_for_assignment(assignment, date):
    end = date + relativedelta(days=5)
    blocks = assignment.blocks.filter(date__gte=date, date__lte=end)
    hours = blocks.aggregate(hours=Sum('hours'))['hours']
    if not hours:
        hours = ''
    return hours


@register.simple_tag
def hours_for_week(contact, date):
    end = date + relativedelta(days=5)
    blocks = ContractBlock.objects.filter(assignment__contact=contact,
                                          date__gte=date, date__lte=end)
    hours = blocks.aggregate(hours=Sum('hours'))['hours']
    if not hours:
        hours = ''
    return hours

