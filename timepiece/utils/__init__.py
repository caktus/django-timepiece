import datetime
from dateutil.relativedelta import relativedelta

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from timepiece.defaults import TimepieceDefaults


class ActiveEntryError(Exception):
    """A user should have no more than one active entry at a given time."""
    pass


def add_timezone(value, tz=None):
    """If the value is naive, then the timezone is added to it.

    If no timezone is given, timezone.get_current_timezone() is used.
    """
    tz = tz or timezone.get_current_timezone()
    try:
        if timezone.is_naive(value):
            return timezone.make_aware(value, tz)
    except AttributeError:  # 'datetime.date' object has no attribute 'tzinfo'
        dt = datetime.datetime.combine(value, datetime.time())
        return timezone.make_aware(dt, tz)
    return value


def get_active_entry(user, select_for_update=False):
    """Returns the user's currently-active entry, or None."""
    entries = apps.get_model('entries', 'Entry').no_join
    if select_for_update:
        entries = entries.select_for_update()
    entries = entries.filter(user=user, end_time__isnull=True)

    if not entries.exists():
        return None
    if entries.count() > 1:
        raise ActiveEntryError('Only one active entry is allowed.')
    return entries[0]


def get_hours_summary(entries):
    hours = {
        'total': 0,
        'billable': 0,
        'non_billable': 0,
    }
    for entry in entries:
        hours['total'] += entry['hours']
        status = 'billable' if entry['billable'] else 'non_billable'
        hours[status] += entry['hours']
    return hours


def get_last_billable_day(day=None):
    day = day or datetime.date.today()
    day += relativedelta(months=1)
    return get_week_start(get_month_start(day)) - relativedelta(days=1)


def get_month_start(day=None):
    """Returns the first day of the given month."""
    day = add_timezone(day or datetime.date.today())
    return day.replace(day=1)


defaults = TimepieceDefaults()


def get_setting(name, **kwargs):
    """Returns the user-defined value for the setting, or a default value."""
    if hasattr(settings, name):  # Try user-defined settings first.
        return getattr(settings, name)
    if 'default' in kwargs:  # Fall back to a specified default value.
        return kwargs['default']
    if hasattr(defaults, name):  # If that's not given, look in defaults file.
        return getattr(defaults, name)
    msg = '{0} must be specified in your project settings.'.format(name)
    raise AttributeError(msg)


def get_week_start(day=None):
    """Returns the Monday of the given week."""
    day = add_timezone(day or datetime.date.today())
    days_since_monday = day.weekday()
    if days_since_monday != 0:
        day = day - relativedelta(days=days_since_monday)
    return day


def get_year_start(day=None):
    """Returns January 1 of the given year."""
    day = add_timezone(day or datetime.date.today())
    return day.replace(month=1).replace(day=1)


def to_datetime(date):
    """Transforms a date or datetime object into a date object."""
    return datetime.datetime(date.year, date.month, date.day)
