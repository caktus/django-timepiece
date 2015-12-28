import datetime, calendar
from dateutil.relativedelta import relativedelta

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from timepiece.defaults import TimepieceDefaults



def chunk_list(seq,max_chunk_size):
  out = []
  last = 0
  if max_chunk_size < 1:
      return seq

  while last < len(seq):
    out.append(seq[last:last + max_chunk_size])
    last += max_chunk_size

  return out


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

def remove_timezone(value):
    if timezone.is_aware(value):
        return datetime.datetime(value.year, value.month, value.day,
            value.hour, value.minute, value.second)
    else:
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
    """Returns the start of week, based on setting of the given week."""
    dow_start = get_setting('TIMEPIECE_WEEK_START', default=0)
    day = add_timezone(day or datetime.date.today())
    while day.weekday() != dow_start:
        day = day - relativedelta(days=1)
    return day


def get_period_start(day=None):
    """Returns the start date of the period (1st or 15th)."""
    # day = add_timezone(day or datetime.date.today())
    # if day.day < 16:
    #     day = day.replace(day=1)
    # else:
    #     day = day.replace(day=16)
    # return datetime.datetime.combine(day, datetime.datetime.min.time())
    return get_week_start(day)

def get_period_end(period_start):
    """Returns end date of the period
    (15th, 28th, 29th, 30th, or 31st).
    """
    # if period_start.day == 1:
    #     period_end = period_start.replace(day=15)
    # else:
    #     period_end = period_start.replace(
    #         day=calendar.monthrange(
    #             period_start.year, period_start.month)[1])
    # return datetime.datetime.combine(
    #     period_end, datetime.datetime.max.time())
    return period_start + relativedelta(days=7) # double check this

def get_weekdays_count(period_start, period_end):
    """Returns the count oc weekdays in period."""
    # weekdays = 0
    # cur_date = period_start
    # while cur_date < period_end:
    #     if cur_date.weekday() <= 4:
    #         weekdays += 1
    #     cur_date += relativedelta(days=1)
    # return weekdays
    return 5

def get_period_dates(period_start, period_end=None):
    """Returns list of period_dates dictionary."""
    period_dates = []
    cur_date = period_start
    period_end = period_end or (period_start + relativedelta(days=1))
    while cur_date < period_end:
        period_dates.append({'date': cur_date.strftime('%Y-%m-%d'),
                             'display': cur_date.strftime('%a %b %d'),
                             'weekday': cur_date.weekday()<=4})
        cur_date += relativedelta(days=1)
    return period_dates

def get_year_start(day=None):
    """Returns January 1 of the given year."""
    day = add_timezone(day or datetime.date.today())
    return day.replace(month=1).replace(day=1)


def to_datetime(date):
    """Transforms a date or datetime object into a date object."""
    return datetime.datetime(date.year, date.month, date.day)

def get_bimonthly_dates(start_date):
    if start_date.day <= 15:
        start = datetime.datetime(start_date.year, start_date.month, 1)
        end = datetime.datetime(start_date.year, start_date.month, 16)
    else:
        start = datetime.datetime(start_date.year, start_date.month, 16)
        if start_date.month < 12:
            end = datetime.datetime(start_date.year, start_date.month+1, 1)
        else:
            end = datetime.datetime(start_date.year+1, 1, 1)
    return (start,end)
