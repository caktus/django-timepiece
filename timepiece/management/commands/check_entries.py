from functools import reduce
from optparse import make_option

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from timepiece import utils
from timepiece.entries.models import Entry


class Command(BaseCommand):
    """
    Management command to check entries for overlapping times.
    Use ./manage.py check_entries --help for more details
    """
    # boiler plate for console programs using optparse
    args = '[<first or last name>] [<first or last name>] ...'
    help = ("Check the database for time entries that overlap.\n"
            "Use --help for options.")

    option_list = BaseCommand.option_list + (
        make_option('--thisweek',
                    action='store_true',
                    dest='week',
                    default=False,
                    help='Show entries from this week only'),
        make_option('--thismonth',
                    action='store_true',
                    dest='month',
                    default=False,
                    help='Show entries from this month only'),
        make_option('-y', '--thisyear',
                    action='store_true',
                    dest='year',
                    default=False,
                    help='Show entries from this year only'),
        make_option('-a', '--all', '--forever',
                    action='store_true',
                    dest='all',
                    default=False,
                    help='Show entries from all recorded history'),
        make_option('-d', '--days',
                    dest='days',
                    type='int',
                    default=0,
                    help='Show entries for the last n days only'),
    )

    def usage(self, subcommand):
        usage = "python manage.py check_entries {} [options]\n\n{}".format(
            self.args, self.help)
        return usage

    def handle(self, *args, **kwargs):
        verbosity = kwargs.get('verbosity', 1)
        start = self.find_start(**kwargs)
        users = self.find_users(*args)
        self.show_init(start, *args, **kwargs)

        all_entries = self.find_entries(users, start, *args, **kwargs)
        all_overlaps = self.check_all(all_entries, *args, **kwargs)
        if verbosity >= 1:
            self.stdout.write('Total overlapping entries: %d' % all_overlaps)

    def check_all(self, all_entries, *args, **kwargs):
        """
        Go through lists of entries, find overlaps among each, return the total
        """
        all_overlaps = 0
        while True:
            try:
                user_entries = all_entries.next()
            except StopIteration:
                return all_overlaps
            else:
                user_total_overlaps = self.check_entry(
                    user_entries, *args, **kwargs)
                all_overlaps += user_total_overlaps

    def check_entry(self, entries, *args, **kwargs):
        """
        With a list of entries, check each entry against every other
        """
        verbosity = kwargs.get('verbosity', 1)
        user_total_overlaps = 0
        user = ''
        for index_a, entry_a in enumerate(entries):
            # Show the name the first time through
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
            self.stdout.write('Total overlapping entries for user ' +
                              '%(first)s %(last)s: %(total)d' % overlap_data)
        return user_total_overlaps

    def find_start(self, **kwargs):
        """
        Determine the starting point of the query using CLI keyword arguments
        """
        week = kwargs.get('week', False)
        month = kwargs.get('month', False)
        year = kwargs.get('year', False)
        days = kwargs.get('days', 0)
        # If no flags are True, set to the beginning of last billing window
        # to assure we catch all recent violations
        start = timezone.now() - relativedelta(months=1, day=1)
        # Set the start date based on arguments provided through options
        if week:
            start = utils.get_week_start()
        if month:
            start = timezone.now() - relativedelta(day=1)
        if year:
            start = timezone.now() - relativedelta(day=1, month=1)
        if days:
            start = timezone.now() - relativedelta(days=days)
        start -= relativedelta(hour=0, minute=0, second=0, microsecond=0)
        return start

    def find_users(self, *args):
        """
        Returns the users to search given names as args.
        Return all users if there are no args provided.
        """
        if args:
            names = reduce(lambda query, arg: query |
                (Q(first_name__icontains=arg) | Q(last_name__icontains=arg)),
                args, Q())  # noqa
            users = User.objects.filter(names)
        # If no args given, check every user
        else:
            users = User.objects.all()
        # Display errors if no user was found
        if not users.count() and args:
            if len(args) == 1:
                raise CommandError('No user was found with the name %s' % args[0])
            else:
                arg_list = ', '.join(args)
                raise CommandError('No users found with the names: %s' % arg_list)
        return users

    def find_entries(self, users, start, *args, **kwargs):
        """
        Find all entries for all users, from a given starting point.
        If no starting point is provided, all entries are returned.
        """
        forever = kwargs.get('all', False)
        for user in users:
            if forever:
                entries = Entry.objects.filter(user=user).order_by('start_time')
            else:
                entries = Entry.objects.filter(
                    user=user, start_time__gte=start).order_by(
                    'start_time')
            yield entries

    # output methods
    def show_init(self, start, *args, **kwargs):
        forever = kwargs.get('all', False)
        verbosity = kwargs.get('verbosity', 1)
        if forever:
            if verbosity >= 1:
                self.stdout.write(
                    'Checking overlaps from the beginning of time')
        else:
            if verbosity >= 1:
                self.stdout.write(
                    'Checking overlap starting on: ' + start.strftime('%m/%d/%Y'))

    def show_name(self, user):
        self.stdout.write('Checking %s %s...' % (user.first_name, user.last_name))

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
            output = ('Entry %(entry)d for %(first_name)s %(last_name)s from '
                      '%(start)s to %(end)s on %(project)s overlaps ' % data_a +
                      'entry %(entry)d from %(start)s to %(end)s on '
                      '%(project)s.' % data_b)
        else:
            output = ('Entry %(entry)d for %(first_name)s %(last_name)s from '
                      '%(start)s to %(end)s on %(project)s overlaps '
                      'with another entry.' % data_a)
        if kwargs.get('verbosity', 1):
            self.stdout.write(output)
