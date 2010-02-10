from django import template
from timepiece.models import PersonRepeatPeriod

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
