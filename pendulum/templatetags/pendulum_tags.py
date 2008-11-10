from django import template
from pendulum.models import Entry
from pendulum import utils
from datetime import datetime, timedelta, time

register = template.Library()

def seconds_for_entries(entries):
    seconds = [e.get_seconds() for e in entries]
    return sum(seconds)

def total_hours_for_period(period, user=None):
    """
    Determines how many hours have been logged for the current period.
    """

    # find all entries in the period
    entries = Entry.objects.in_period(period, user)

    # put each entry's total hours in a list
    hours = [e.total_hours for e in entries]

    # add up all items in the list
    return sum(hours)

def total_time_for_period(period, user=None):
    """
    Determines how much time has been logged for the current period.
    """

    # find all entries in the period
    entries = Entry.objects.in_period(period, user)

    seconds = seconds_for_entries(entries)
    return utils.get_total_time(seconds)

class EntriesProjectsOrActivitiesNode(template.Node):
    """
    Finds all projects or activities for a list of entries.  This tag is used to
    limit the statistics table to only those projects and activities which have
    been logged in the specified period.
    """

    def __init__(self, entries, varname, projects=False, activities=False):
        self.entries = template.Variable(entries)
        self.varname = varname
        self.projects = projects
        self.activities = activities

    def render(self, context):
        # pull back the actual entries from the context
        entries = self.entries.resolve(context)
        collection = []

        if self.projects:
            # if we're getting projects...
            # iterate through all of the entries
            for entry in entries:
                # make sure we have a valid project that is not in the collection
                if entry.project and entry.project not in collection:
                    # add the project to the collection
                    collection.append(entry.project)

        elif self.activities:
            # if we're getting activities...
            # iterate through all of the entries
            for entry in entries:
                # make sure we have a valid activity that is not in the
                # collection
                if entry.activity and entry.activity not in collection:
                    # add the activity to the collection
                    collection.append(entry.activity)

        # put the collection into the context
        context[self.varname] = collection
        return ''

def entries_projects(parser, token):
    """
    Tag for pulling back all projects that were used in a list of entries
    """
    try:
        t, entries, a, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('entries_projects usage: {% entries_projects entries as projects %}')

    return EntriesProjectsOrActivitiesNode(entries, varname, projects=True)

def entries_activities(parser, token):
    """
    Tag for pulling back all activities that were used in a list of entries
    """
    try:
        t, entries, a, varname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('entries_activities usage: {% entries_activities entries as activities %}')

    return EntriesProjectsOrActivitiesNode(entries, varname, activities=True)

class TimeInPeriodNode(template.Node):
    """
    Determines how many hours were logged during the specified period for a
    project or an activity (or any other object with an "entries" attribute).
    """
    def __init__(self, obj, period, time=False):
        self.obj = template.Variable(obj)
        self.period = template.Variable(period)
        self.time = time

    def render(self, context):
        # pull the object back from the context
        obj = self.obj.resolve(context)

        # determine the period specified
        period = self.period.resolve(context)

        # find all entries in that period
        entries = obj.entries.in_period(period, context['user'])

        if self.time:
            seconds = seconds_for_entries(entries)
            return utils.get_total_time(seconds)
        else:
            hours = [e.total_hours for e in entries]
            return float(sum(hours))

def hours_in_period(parser, token):
    """
    Used to determine how many hours were logged for a particular project or
    activitiy during the specified period.
    """
    try:
        t, obj, period = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('hours_in_period usage: {% hours_in_period project period %}')

    return TimeInPeriodNode(obj, period)

def time_in_period(parser, token):
    """
    Used to determine how much time was logged for a particular project or
    activitiy during the specified period.
    """
    try:
        t, obj, period = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('time_in_period usage: {% time_in_period project period %}')

    return TimeInPeriodNode(obj, period, time=True)

class DayTotalsNode(template.Node):
    def __init__(self, date_obj):
        self.date_obj = template.Variable(date_obj)

    def render(self, context):
        date_obj = self.date_obj.resolve(context)
        entries = Entry.objects.filter(start_time__year=date_obj.year,
                                       start_time__month=date_obj.month,
                                       start_time__day=date_obj.day,
                                       user=context['user'])

        # If there is only one (or 0) entry for a particular day, there's no
        # need to go any further
        if len(entries) <= 1: return ''

        hours = [e.total_hours for e in entries]
        total = sum(hours)

        context['day_total'] = total
        context['day_time'] = utils.get_total_time(seconds_for_entries(entries))
        context['day'] = date_obj

        t = template.loader.get_template('pendulum/_day_totals.html')
        return t.render(context)

def day_totals(parser, token):
    """
    Calculates how many total hours were worked in a given day
    """

    try:
        t, date_obj = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('day_totals usage: {% day_totals entry.start_time.date_obj %}')

    return DayTotalsNode(date_obj)

def week_bounds(year, week):
    """
    Finds the beginning and end of a week given a year and week number
    Source: http://bytes.com/forum/thread499819.html
    """
    # TODO: Make sure this work with weeks that don't begin on Sunday
    startOfYear = datetime(year, 1, 1)
    week0 = startOfYear - timedelta(days=startOfYear.isoweekday())
    sun = week0 + timedelta(weeks=week)
    sat = (sun + timedelta(days=6))
    return sun, datetime.combine(sat, time(23, 59, 59))

class WeekTotalsNode(template.Node):
    def __init__(self, date_obj):
        self.date_obj = template.Variable(date_obj)

    def render(self, context):
        date_obj = self.date_obj.resolve(context)

        date_range = week_bounds(date_obj.year, int(date_obj.strftime('%U')))
        entries = Entry.objects.filter(start_time__range=date_range,
                                       user=context['user'])

        # If there is only one (or 0) entry for a particular week, there's no
        # need to go any further
        if len(entries) <= 1: return ''

        hours = [e.total_hours for e in entries]
        total = sum(hours)

        context['week_total'] = total
        context['week_time'] = utils.get_total_time(seconds_for_entries(entries))
        context['week_range'] = {'start': date_range[0],
                                 'end': date_range[1]}

        t = template.loader.get_template('pendulum/_week_totals.html')
        return t.render(context)

def week_totals(parser, token):
    """
    Calculates how many total hours were worked in a given week
    """

    try:
        t, date_obj = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('week_totals usage: {% week_totals entry.start_time %}')

    return WeekTotalsNode(date_obj)

register.simple_tag(total_hours_for_period)
register.simple_tag(total_time_for_period)
register.tag(entries_projects)
register.tag(entries_activities)
register.tag(hours_in_period)
register.tag(time_in_period)
register.tag(day_totals)
register.tag(week_totals)
