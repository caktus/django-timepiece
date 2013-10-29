from dateutil.relativedelta import relativedelta
from itertools import groupby, repeat
from collections import defaultdict

from django.db.models import Sum

from timepiece.utils import add_timezone, get_hours_summary, get_week_start


def daily_summary(day_entries):
    projects = {}
    all_day = {}
    for name, entries in groupby(day_entries, lambda x: x['project__name']):
        hours = get_hours_summary(entries)
        projects[name] = hours
        for key in hours.keys():
            if key in all_day:
                all_day[key] += hours[key]
            else:
                all_day[key] = hours[key]
    return (all_day, projects)


def grouped_totals(entries):
    select = {
        "day": {"date": """DATE_TRUNC('day', end_time)"""},
        "week": {"date": """DATE_TRUNC('week', end_time)"""},
    }
    weekly = entries.extra(select=select["week"]).values('date', 'billable')
    weekly = weekly.annotate(hours=Sum('hours')).order_by('date')
    daily = entries.extra(select=select["day"]).values('date', 'project__name',
                                                       'billable')
    daily = daily.annotate(hours=Sum('hours')).order_by('date',
                                                        'project__name')
    weeks = {}
    for week, week_entries in groupby(weekly, lambda x: x['date']):
        if week is not None:
            week = add_timezone(week)
        weeks[week] = get_hours_summary(week_entries)
    days = []
    last_week = None
    for day, day_entries in groupby(daily, lambda x: x['date']):
        week = get_week_start(day)
        if last_week and week > last_week:
            yield last_week, weeks.get(last_week, {}), days
            days = []
        days.append((day, daily_summary(day_entries)))
        last_week = week
    yield week, weeks.get(week, {}), days


def grouped_user_hours(contract, project):
    entries = contract.entries(projects=[project]).date_trunc('day')
    user_hours = defaultdict(list)
    # TODO: Move user_hours calculation into separate function
    for user, entries in groupby(entries, lambda e: e['user']):
        previous_date = contract.start_date - relativedelta(days=1)
        indexed_dated_entries = enumerate(groupby(entries, lambda e: e['date']))
        for index, (date_time, date_entries) in indexed_dated_entries:
            if index == 0:
                for entry_datum in date_entries:
                    user_name = u' '.join((
                        entry_datum['user__first_name'],
                        entry_datum['user__last_name']
                    ))
                    break;
            delta_days = (date_time.date() - previous_date).days
            user_hours[user_name].extend(repeat(0, delta_days - 1))
            user_hours[user_name].append(sum(d['hours'] for d in date_entries))
            previous_date = date_time.date()
        remaining_days = (contract.end_date - previous_date).days
        user_hours[user_name].extend(repeat(0, remaining_days))
    return user_hours
