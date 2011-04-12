from django import template

register = template.Library()

@register.filter
def _abs(num):
    return abs(num)

register.filter('abs', _abs)

