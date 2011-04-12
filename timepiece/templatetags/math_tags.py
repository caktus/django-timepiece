from django import template

register = template.Library()

@register.filter
def _abs(num):
    try:
        num = float(num)
    except ValueError:
        return 0
    return abs(num)

register.filter('abs', _abs)

