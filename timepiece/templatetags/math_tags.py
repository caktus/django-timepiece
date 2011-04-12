from django import template

register = template.Library()

register.filter('abs', lambda x: abs(x))

