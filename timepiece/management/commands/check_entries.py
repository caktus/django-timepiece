import pprint
import datetime
from optparse import OptionParser, make_option

from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import models as auth_models
from django.db.models import Q
from django.conf import settings
from django.db import transaction

from timepiece import utils

from timepiece import models as timepiece


class Command(BaseCommand):
    """
    Management command to check entries for overlapping times.
    Use ./manage.py check_entries --help for more details
    """
    #boiler plate for console programs using optparse
    args = '<user\'s first or last name or user.id> <user\'s first...>...'
    help = """Check the database for entries that overlap.
    Use --help for options"""
    parser = OptionParser()
    parser.usage += """
./manage.py check_entries [<first or last name1> <name2>...<name n>] [OPTIONS]

For options type:
./manage.py check_entries --help
    """

    def make_options(self, *args, **kwargs):
        """
        Define the arguments that can be used with this command
        """
        return (
        #Jenkins arguments to ignore
        make_option('--pep8-exclude',
            dest='ignore_pep8',
            type='str',
            default='',
            help='Jenkins only'),
        ) + (
        make_option('--coverage-exclude',
            dest='ignore_coverage',
            type='str',
            default='',
            help='Jenkins only'),
        ) + (
        make_option('--thisweek',
            action='store_true',
            dest='week',
            default=False,
            help='Show entries from this week only'),
        ) + (
        make_option('--thismonth',
            action='store_true',
            dest='month',
            default=False,
            help='Show entries from this month only'),
        ) + (
        make_option('-y', '--thisyear',
            action='store_true',
            dest='year',
            default=False,
            help='Show entries from this year only'),
        ) + (
        make_option('-a', '--all', '--forever',
            action='store_true',
            dest='all',
            default=False,
            help='Show entries from all recorded history'),
        ) + (
        make_option('-d', '--days',
            dest='days',
            type='int',
            default=0,
            help='Show entries for the last n days only'),
        )

    option_list = BaseCommand.option_list + make_options(*args)
    parser.add_options(option_list)
    (options, args) = parser.parse_args()

    def handle(self, *args, **kwargs):
        """
        main()
        """
        verbosity = kwargs.get('verbosity', 1)
        start = self.find_start(**kwargs)
        people = self.find_people(*args)
        self.show_init(start, *args, **kwargs)
        all_entries = self.find_entries(people, start, *args, **kwargs)
        all_overlaps = self.check_all(all_entries, *args, **kwargs)
        if verbosity >= 1:
            print 'Total overlapping entries: %d' % all_overlaps

    def check_all(self, all_entries, *args, **kwargs):
        """
        Go through lists of entries, find overlaps among each, return the total
        """
        all_overlaps = 0
        while True:
            try:
                person_entries = all_entries.next()
            except StopIteration:
                return all_overlaps
            else:
                user_total_overlaps = self.check_entry(
                    person_entries, *args, **kwargs)
                all_overlaps += user_total_overlaps

    def check_entry(self, entries, *args, **kwargs):
        """
        With a list of entries, check each entry against every other
        """
        verbosity = kwargs.get('verbosity', 1)
        user_total_overlaps = 0
        user = ''
        for index_a, entry_a in enumerate(entries):
            #Show the name the first time through
            if index_a == 0:
                if args and verbosity >= 1 or verbosity >= 2:
                    self.show_name(entry_a.user)
                    user = entry_a.user
            for index_b in range(index_a, len(entries)):
                entry_b = entries[index_b]
                if entry_a.check_overlap(entry_b):
                    user_total_overlaps += 1
                    self.show_overlap(entry_a, entry_b, verbosity=verbosity)
        if user_total_overlaps and user and verbosity >= 1:
            overlap_data = {
                'first': user.first_name,
                'last': user.last_name,
                'total': user_total_overlaps,
            }
            print 'Total overlapping entries for user ' + \
                '%(first)s %(last)s: %(total)d' % overlap_data
        return user_total_overlaps

    def find_start(self, **kwargs):
        """
        Determine the starting point of the query using CLI keyword arguments
        """
        week = kwargs.get('week', False)
        month = kwargs.get('month', False)
        year = kwargs.get('year', False)
        days = kwargs.get('days', 0)
        #If no flags are True, set to the beginning of last billing window
        #to assure we catch all recent violations
        start = datetime.datetime.now() - relativedelta(months=1, day=1)
        #Set the start date based on arguments provided through options
        if week:
            start = utils.get_week_start()
        if month:
            start = datetime.datetime.now() - relativedelta(day=1)
        if year:
            start = datetime.datetime.now() - relativedelta(day=1, month=1)
        if days:
            start = datetime.datetime.now() - \
            datetime.timedelta(days=days)
        start = start - relativedelta(
            hour=0, minute=0, second=0, microsecond=0)
        return start

    def find_people(self, *args):
        """
        Returns the users to search given names as args.
        Return all users if there are no args provided.
        """
        if args:
            names = reduce(lambda query, arg: query |
                (Q(first_name__icontains=arg) | Q(last_name__icontains=arg)),
                args, Q())
            people = auth_models.User.objects.filter(names)
        #If no args given, check every user
        else:
            people = auth_models.User.objects.all()
        #Display errors if no user was found
        if not people.count() and args:
            if len(args) == 1:
                raise CommandError('No user was found with the name %s' \
                % args[0])
            else:
                arg_list = ', '.join(args)
                raise CommandError('No users found with the names: %s' \
                % arg_list)
        return people

    def find_entries(self, people, start, *args, **kwargs):
        """
        Find all entries for all users, from a given starting point.
        If no starting point is provided, all entries are returned.
        """
        forever = kwargs.get('all', False)
        for person in people:
            if forever:
                entries = timepiece.Entry.objects.filter(
                    user=person).order_by(
                    'start_time')
            else:
                entries = timepiece.Entry.objects.filter(
                    user=person, start_time__gte=start).order_by(
                    'start_time')
            yield entries

    #output methods
    def show_init(self, start, *args, **kwargs):
        forever = kwargs.get('all', False)
        verbosity = kwargs.get('verbosity', 1)
        if forever:
            if verbosity >= 1:
                print 'Checking overlaps from the beginning ' + \
                    'of time'
        else:
            if verbosity >= 1:
                print 'Checking overlap starting on: ' + \
                    start.strftime('%m/%d/%Y')

    def show_name(self, person):
        print 'Checking %s %s...' % \
        (person.first_name, person.last_name)

    def show_overlap(self, entry_a, entry_b=None, **kwargs):
        def make_output_data(entry):
            return{
                'first_name': entry.user.first_name,
                'last_name': entry.user.last_name,
                'entry': entry.id,
                'start': entry.start_time,
                'end': entry.end_time,
                'project': entry.project
            }
        data_a = make_output_data(entry_a)
        if entry_b:
            data_b = make_output_data(entry_b)
            output = 'Entry %(entry)d for %(first_name)s %(last_name)s from ' \
            % data_a + '%(start)s to %(end)s on %(project)s overlaps ' \
            % data_a + 'entry %(entry)d from %(start)s to %(end)s on ' \
            % data_b + '%(project)s.' % data_b
        else:
            output = 'Entry %(entry)d for %(first_name)s %(last_name)s from ' \
            % data_a + '%(start)s to %(end)s on %(project)s overlaps ' \
            % data_a + 'with another entry.'
        if kwargs.get('verbosity', 1):
            print output
