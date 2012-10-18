from django.conf import settings


class TimepieceDefaults(object):

    @property
    def FAMFAMFAM_URL(self):
        return getattr(settings, 'STATIC_URL', '/') + 'images/icons/'

    EXTRA_NAV = {}

    TIMEPIECE_DEFAULT_LOCATION_SLUG = None

    TIMEPIECE_PROJECTS = {}

    TRAC_URL = lambda slug: '/%s' % slug
