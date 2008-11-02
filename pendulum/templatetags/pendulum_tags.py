from django import template
from pendulum.models import Entry

register = template.Library()

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

class HoursInPeriodNode(template.Node):
    """
    Determines how many hours were logged during the specified period for a
    project or an activity (or any other object with an "entries" attribute).
    """
    def __init__(self, obj, period):
        self.obj = template.Variable(obj)
        self.period = template.Variable(period)

    def render(self, context):
        # pull the object back from the context
        obj = self.obj.resolve(context)

        # determine the period specified
        period = self.period.resolve(context)

        # find all entries in that period
        entries = obj.entries.in_period(period, context['user'])
        hours = [e.total_hours for e in entries]
        return sum(hours)

def hours_in_period(parser, token):
    """
    Used to determine how many hours were logged for a particular project or
    activitiy during the specified period.
    """
    try:
        t, obj, period = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('hours_in_period usage: {% hours_in_period project period %}')

    return HoursInPeriodNode(obj, period)

register.simple_tag(total_hours_for_period)
register.tag(entries_projects)
register.tag(entries_activities)
register.tag(hours_in_period)
