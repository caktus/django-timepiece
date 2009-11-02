from django import template

register = template.Library()


@register.filter
def seconds_to_hours(seconds):
    return round(seconds/3600.0, 2)
