from django.conf import settings


class TimepieceDefaults(object):

    @property
    def TIMEPIECE_ICON_URL(self):
        return getattr(settings, 'STATIC_URL', '/') + 'images/icons/'

    TIMEPIECE_EXTRA_NAV = {}

    TIMEPIECE_DEFAULT_LOCATION_SLUG = None

    TIMEPIECE_PAID_LEAVE_PROJECTS = {}

    TIMEPIECE_TRACKER_URL_FUNC = lambda slug: '/%s' % slug
