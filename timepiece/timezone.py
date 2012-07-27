import datetime
import pytz

from django.conf import settings


def make_aware(value, tz):
    """
    Make a date/datetime timezone aware using a given timezone
    """
    if hasattr(tz, 'localize'):
        return tz.localize(value, is_dst=None)
    else:
        return value.replace(tzinfo=tz)


def now():
    """
    If USE_TZ is set (default on Django 1.4), return an aware datetime
    """
    if getattr(settings, 'USE_TZ', None):
        return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    return datetime.datetime.now()


def is_aware(date):
    """
    Check if a datetime is aware
    """
    return date.tzinfo is not None and date.tzinfo.utcoffset(date) is not None


def is_naive(date):
    """
    Check if a datetime is naive
    """
    return date.tzinfo is None or date.tzinfo.utcoffset(date) is None


def get_current_timezone():
    """
    Return the timezone set in project settings or Eastern time by default
    """
    tz = getattr(settings, 'TIME_ZONE', 'US/Eastern')
    return pytz.timezone(tz)
