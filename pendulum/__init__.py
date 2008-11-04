VERSION = (0, 1, 6, 'pre')

def version():
    return '%s.%s.%s-%s' % VERSION

def get_version():
    print 'Pendulum %s' % version()
