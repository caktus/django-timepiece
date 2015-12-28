from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.test import TestCase

from timepiece import utils
from timepiece.management.commands import check_entries
from timepiece.entries.models import Entry

from . import factories


class CheckEntries(TestCase):

    def setUp(self):
        super(CheckEntries, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        self.project = factories.Project(
            type__enable_timetracking=True, status__enable_timetracking=True,
            point_person=self.user)

        self.default_data = {
            'user': self.user,
            'project': self.project,
            'seconds_paused': 0,
            'status': Entry.VERIFIED,
        }
        self.good_start = timezone.now() - relativedelta(days=0, hours=8)
        self.good_end = timezone.now() - relativedelta(days=0)
        self.bad_start = timezone.now() - relativedelta(days=1, hours=8)
        self.bad_end = timezone.now() - relativedelta(days=1)
        # Create users for the test
        self.user.first_name = 'first1'
        self.user.last_name = 'last1'
        self.user.save()
        self.user2.first_name = 'first2'
        self.user2.last_name = 'last2'
        self.user2.save()
        self.all_users = [self.user, self.user2, self.superuser]
        # Create a valid entry for all users on every day since 60 days ago
        self.make_entry_bulk(self.all_users, 60)

    # helper functions
    def make_entry(self, **kwargs):
        """
        Make a valid or invalid entry
        make_entry(**kwargs)
        **kwargs can include: start_time, end_time, valid
        Without any kwargs, make_entry makes a valid entry. (first time called)
        With valid=False, makes an invalid entry
        start_time and end_time can be specified.
        If start_time is used without end_time, end_time is 10 mintues later
        """
        valid = kwargs.get('valid', True)
        if valid:
            default_start = self.good_start
            default_end = self.good_end
        else:
            default_start = self.bad_start
            default_end = self.bad_end
        user = kwargs.get('user', self.user)
        start = kwargs.get('start_time', default_start)
        if 'end_time' in kwargs:
            end = kwargs.get('end_time', default_end)
        else:
            if 'start_time' in kwargs:
                end = start + relativedelta(minutes=10)
            else:
                end = default_end
        data = self.default_data
        data.update({
            'user': user,
            'start_time': start,
            'end_time': end,
        })
        factories.Entry(**data)

    def make_entry_bulk(self, users, days, *args, **kwargs):
        """
        Create entries for users listed, from n days ago (but not today)
        make_entry_bulk(users_list, num_days)
        """
        # Test cases may create overlapping entries later
        for user in users:
            self.default_data.update({'user': user})
            # Range uses 1 so that good_start/good_end use today as valid times.
            for day in range(1, days + 1):
                self.default_data.update({
                    'start_time': timezone.now() - relativedelta(days=day, minutes=1),
                    'end_time': timezone.now() - relativedelta(days=day,)
                })
                factories.Entry(**self.default_data)

    # tests
    def testFindStart(self):
        """
        With various kwargs, find_start should return the correct date
        """
        # Establish some datetimes
        now = timezone.now()
        today = now - relativedelta(
            hour=0, minute=0, second=0, microsecond=0)
        last_billing = today - relativedelta(months=1, day=1)
        yesterday = today - relativedelta(days=1)
        ten_days_ago = today - relativedelta(days=10)
        thisweek = utils.get_week_start(today)
        thismonth = today - relativedelta(day=1)
        thisyear = today - relativedelta(month=1, day=1)
        # Use command flags to obtain datetimes
        start_default = check_entries.Command().find_start()
        start_yesterday = check_entries.Command().find_start(days=1)
        start_ten_days_ago = check_entries.Command().find_start(days=10)
        start_of_week = check_entries.Command().find_start(week=True)
        start_of_month = check_entries.Command().find_start(month=True)
        start_of_year = check_entries.Command().find_start(year=True)
        # assure the returned datetimes are correct
        self.assertEqual(start_default, last_billing)
        self.assertEqual(start_yesterday, yesterday)
        self.assertEqual(start_ten_days_ago, ten_days_ago)
        self.assertEqual(start_of_week, thisweek)
        self.assertEqual(start_of_month, thismonth)
        self.assertEqual(start_of_year, thisyear)

    def testFindUsers(self):
        """
        With args, find_users should search and return those user objects
        Without args, find_users should return all user objects
        """
        # Find one user by icontains first or last name, return all if no args
        users1 = check_entries.Command().find_users('firsT1')
        users2 = check_entries.Command().find_users('LasT2')
        all_users = check_entries.Command().find_users()
        # obtain instances from the querysets
        user1 = users1.get(pk=self.user.pk)
        user2 = users2.get(pk=self.user2.pk)
        all_1 = all_users.get(pk=self.user.pk)
        all_2 = all_users.get(pk=self.user2.pk)
        all_3 = all_users.get(pk=self.superuser.pk)
        self.assertEqual(users1.count(), 1)
        self.assertEqual(users2.count(), 1)
        self.assertEqual(all_users.count(), 3)
        self.assertEqual(user1, self.user)
        self.assertEqual(user2, self.user2)
        self.assertEqual(all_1, user1)
        self.assertEqual(all_2, user2)
        self.assertEqual(all_3, self.superuser)

    def testFindEntries(self):
        """
        Given a list of users and a starting point, entries should generate a
        list of all entries for each user from that time until now.
        """
        start = check_entries.Command().find_start()
        if start.day == 1:
            start += relativedelta(days=1)
        all_users = check_entries.Command().find_users()
        entries = check_entries.Command().find_entries(all_users, start)
        # Determine the number of days checked
        today = timezone.now() - \
            relativedelta(hour=0, minute=0, second=0, microsecond=0)
        diff = today - start
        days_checked = diff.days
        total_entries = 0
        while True:
            try:
                user_entries = next(entries)
                for entry in user_entries:
                    total_entries += 1
            except StopIteration:
                # Verify that every entry from the start point was returned
                expected_total = days_checked * len(self.all_users)
                self.assertEqual(total_entries, expected_total)
                return

    def testCheckEntry(self):
        """
        Given lists of entries from users, check_entry should return all
        overlapping entries.
        """
        start = check_entries.Command().find_start()
        all_users = check_entries.Command().find_users()
        entries = check_entries.Command().find_entries(all_users, start)
        total_overlaps = 0
        # make some bad entries
        num_days = 5
        self.make_entry_bulk(self.all_users, num_days)
        while True:
            try:
                user_entries = next(entries)
                user_overlaps = check_entries.Command().check_entry(
                    user_entries, verbosity=0)
                total_overlaps += user_overlaps
            except StopIteration:
                self.assertEqual(
                    total_overlaps, num_days * len(self.all_users))
                return
