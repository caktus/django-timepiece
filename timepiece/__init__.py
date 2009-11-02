VERSION = (0, 0, 1, '')

def version():
    return '%s.%s.%s-%s' % VERSION

def get_version():
    return 'django-timepiece %s' % version()
