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
        start = self.find_start(**kwargs)
        people = self.find_people(*args)
        self.show_init(start, *args, **kwargs)
        for person in people:
            entries = self.find_entries(person, start, *args, **kwargs)
            for entry in entries:
                if args and verbosity == 1 or \
                not entries.count() and verbosity == 2:
                    self.show_name(person)
                if entry.is_overlapping():
                    self.show_overlap(person, entry)

    def find_start(self, **kwargs):
        """
        Determine the starting point of the query using CLI keyword arguments
        """
        week = kwargs.get('week', False)
        month = kwargs.get('month', False)
        year = kwargs.get('year', False)
        days = kwargs.get('days', 0)
        #If no flags are True, set to 2 months ago
        start = datetime.datetime.now() - datetime.timedelta(weeks=8)
        #Set the start date based on arguments provided through options
        if week:
            start = utils.get_week_start()
        if month:
            start = datetime.datetime.now() - relativedelta(day=1)
        if year:
            start = datetime.datetime.now() - relativedelta(day=1, month=1)
        if days:
            start = datetime.datetime.now() - \
            datetime.timedelta(days=self.options.days)
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

    def find_entries(self, person, start, *args, **kwargs):
        """
        Find all entries for a given user, from a given starting point.
        If no starting point is provided, all entries for the user are returned
        """
        forever = kwargs.get('all', False)
        verbosity = kwargs.get('verbosity', 1)
        if forever:
            entries = timepiece.Entry.objects.filter(
                user=person).order_by(
                'start_time')
        else:
            entries = timepiece.Entry.objects.filter(
                user=person, start_time__gte=start).order_by(
                'start_time')
        return entries

    def show_init(self, start, *args, **kwargs):
        forever = kwargs.get('all', False)
        verbosity = kwargs.get('verbosity', 1)
        if forever:
            if verbosity >= 1:
                self.stdout.write('Checking overlaps from the beginning ' + \
                    'of time\n')
        else:
            if verbosity >= 1:
                self.stdout.write('Checking overlap starting at: ' + \
                    str(start) + '\n')

    def show_name(self, person):
        self.stdout.write('Checking %s %s...\n' % \
        (person.first_name, person.last_name))

    def show_overlap(self, person, entry):
        data = {
            'first_name': person.first_name,
            'last_name': person.last_name,
            'entry': entry.id,
            'start_time': entry.start_time,
            'end_time': entry.end_time,
            'project': entry.project
        }
        output = 'Entry %(entry)d for %(first_name)s %(last_name)s from '\
        % data + \
        '%(start_time)s to %(end_time)s on %(project)s overlaps another entry'\
        % data
        self.stdout.write(output + '\n')
