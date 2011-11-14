import datetime
import random
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Sum
from django.contrib.auth.models import User

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.tests.base import TimepieceDataTestCase

from dateutil import relativedelta

from timepiece.projection import run_projection, user_weekly_assignments
from timepiece import utils


class ProjectionTest(TimepieceDataTestCase):

    def setUp(self):
        person = User.objects.create_user('test', 'a@b.com', 'abc')
        self.ps = self.create_person_schedule(data={'user': person})

    def log_time(self, assignment, delta=None, start=None):
        if delta:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = datetime.datetime.now()
        elif not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time())
        end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': assignment.user,
                'start_time': start,
                'end_time': end,
                'project': assignment.contract.project}
        return self.create_entry(data)

    def test_week_start(self):
        """ Test that all days Sun. through Sat. return the previous Monday"""
        monday = datetime.date(2011, 1, 10)
        self.assertEqual(monday, utils.get_week_start(monday))
        sunday = datetime.date(2011, 1, 16)
        self.assertEqual(monday, utils.get_week_start(sunday))
        following_monday = datetime.date(2011, 1, 17)
        saturday = datetime.date(2011, 1, 22)
        self.assertEqual(following_monday, utils.get_week_start(saturday))

    def  test_month_start(self):
        """ Test that any day returns the first day of the month"""
        days = [datetime.date(2011, 1, 1),
                datetime.date(2011, 1, 16),
                datetime.date(2011, 1, 17),
                datetime.date(2011, 1, 22),
                datetime.date(2011, 1, 31),
                ]
        for day in days:
            self.assertEqual(utils.get_month_start(day),
                             datetime.date(2011, 1, 1))

    def test_generate_dates(self):
        """ Test generation of full date ranges """
        ### test WEEKLY
        # 2 weeks
        start = datetime.date(2011, 1, 17)
        end = datetime.date(2011, 1, 29)
        weeks = utils.generate_dates(start=start, end=end)
        self.assertEqual(2, weeks.count())
        # 3 weeks
        start = datetime.date(2011, 1, 17)
        end = datetime.date(2011, 1, 31)
        weeks = utils.generate_dates(start=start, end=end)
        self.assertEqual(3, weeks.count())
        # random weeks
        num = random.randint(5, 20)
        start = utils.get_week_start(datetime.date.today())
        end = start + datetime.timedelta(weeks=num - 1)
        weeks = utils.generate_dates(start=start, end=end)
        self.assertEqual(num, weeks.count())
        ### test MONTHLY
        start = datetime.date(2011, 1, 17)
        end = datetime.date(2011, 4, 29)
        months = utils.generate_dates(start=start, end=end, by='month')
        self.assertEqual(4, months.count())
        for index, month in enumerate(months):
            self.assertEqual(month.date(), datetime.date(2011, index + 1, 1))
        ### test DAILY
        start = datetime.date(2011, 2, 1)
        end = datetime.date(2011, 2, 15)
        days = utils.generate_dates(start=start, end=end, by='day')
        self.assertEqual(15, days.count())
        for index, day in enumerate(days):
            self.assertEqual(day.date(), datetime.date(2011, 2, index + 1))

    def test_week_window(self):
        """ Test generation of weekly window with given date """
        #Tuesday
        day = datetime.date(2011, 2, 1)
        expected_start = datetime.date(2011, 1, 31)
        expected_end = datetime.date(2011, 2, 7)
        start, end = utils.get_week_window(day)
        self.assertEqual(start.toordinal(), expected_start.toordinal())
        self.assertEqual(end.toordinal(), expected_end.toordinal())

    def test_project_contract_remaining_weeks(self):
        """ Test calculation of contract remaining weeks """
        num = random.randint(5, 20)
        start = datetime.date.today()
        end = start + datetime.timedelta(weeks=num - 1)
        pc = self.create_project_contract({'num_hours': 100, 'end_date': end,
                                           'start_date': start})
        self.assertEqual(num, pc.weeks_remaining.count())

    def test_weekly_commmitment(self):
        """ Test calculation of contract assignment's weekly commitment """
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=40)
        self.assertEqual(ca.weekly_commitment(start), 40)

    def test_weekly_commmitment_with_earlier_allocation(self):
        """ Test calculation of contract assignment's weekly commitment """
        # 1 week assignment, 20 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=1) - datetime.timedelta(days=1)
        ca1 = self._assign(start, end, hours=20)
        # allocate 20 hours to this assignment
        ca1.blocks.create(date=start, hours=20)
        # 1 week assignment, 20 hours
        ca2 = self._assign(start, end, hours=20)
        # only 20 hours left this week
        self.assertEqual(ca2.weekly_commitment(start), 20)

    def test_weekly_commmitment_with_look_ahead(self):
        """ Test later assignment's min hours factor into weekly commitment """
        # 1 week assignment, 40 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=1) - datetime.timedelta(days=1)
        ca1 = self._assign(start, end, hours=40)
        # 2 week assignment, 40 hours
        end = start + datetime.timedelta(weeks=1) - datetime.timedelta(days=1)
        ca2 = self._assign(start, end, hours=40)
        ca2.min_hours_per_week = 5
        ca2.save()
        self.assertEqual(ca1.weekly_commitment(start), 35)
        ca1.blocks.create(date=start, hours=35)
        self.assertEqual(ca2.weekly_commitment(start), 5)

    def test_weekly_commmitment_with_hours_worked(self):
        """ Test weekly commitment with previously logged hours """
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=30)
        self.log_time(ca, start=start, delta=(10, 0))
        self.assertEqual(ca.hours_worked, 10)
        self.assertEqual(ca.hours_remaining, 20)
        self.assertEqual(ca.weekly_commitment(start), 30)

    def test_weekly_commitment_over_remaining(self):
        # 1 week assignment, 20 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=1) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=20)
        # only 20 hours left on assignment
        self.assertEqual(ca.weekly_commitment(start), 20)

    def _assign(self, start=None, end=None, hours=30):
        pc = self.create_project_contract({'num_hours': hours,
                                           'start_date': start,
                                           'end_date': end})
        ca = self.create_contract_assignment({'contract': pc,
                                              'user': self.ps.user,
                                              'num_hours': hours})
        return ca

    def test_assignment_active_ends_mid_week(self):
        """ Test manager returns assignments that end before end of window """
        start = utils.get_week_start() - datetime.timedelta(days=2)
        end = start + datetime.timedelta(weeks=1)
        ca = self._assign(start, end)
        week = utils.get_week_start()
        next_week = week + datetime.timedelta(weeks=1)
        assignments = timepiece.ContractAssignment.objects
        assignments = assignments.active_during_week(week, next_week)
        self.assertTrue(assignments.filter(pk=ca.pk).exists())

    def test_assignment_active_starts_mid_week(self):
        """ Test manager returns assignments that start before window """
        start = utils.get_week_start() + datetime.timedelta(days=2)
        end = start + datetime.timedelta(weeks=2)
        ca = self._assign(start, end)
        week = utils.get_week_start()
        next_week = week + datetime.timedelta(weeks=1)
        assignments = timepiece.ContractAssignment.objects
        assignments = assignments.active_during_week(week, next_week)
        self.assertTrue(assignments.filter(pk=ca.pk).exists())

    def test_assignment_active_within_week(self):
        """ Test manager returns assignments that contain entire week """
        start = utils.get_week_start() - datetime.timedelta(weeks=1)
        end = start + datetime.timedelta(weeks=3)
        ca = self._assign(start, end)
        week = utils.get_week_start()
        next_week = week + datetime.timedelta(weeks=1)
        assignments = timepiece.ContractAssignment.objects
        assignments = assignments.active_during_week(week, next_week)
        self.assertTrue(assignments.filter(pk=ca.pk).exists())

    def test_no_remaining_hours(self):
        """ Gurantee no overcommittment """
        # 1 week, 40 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=1) - datetime.timedelta(days=1)
        ca1 = self._assign(start, end, hours=40)
        ca1.blocks.create(date=start, hours=40)
        self.assertEqual(ca1.weekly_commitment(start), 0)
        # 2 weeks, 40 hours
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca2 = self._assign(start, end, hours=40)
        self.assertEqual(ca2.weekly_commitment(start), 0)

    def test_single_assignment_projection(self):
        # 2 weeks, 60 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=60)
        run_projection()
        self.assertEqual(60, ca.blocks.aggregate(s=Sum('hours'))['s'])

    def test_min_hours_per_week_weighted(self):
        """
        Test minimum hours/week with weighting based on assignment end date
        """
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=1)
        ca1 = self._assign(start, end, hours=40)
        ca2 = self._assign(start, end + datetime.timedelta(days=1), hours=40)
        ca1.min_hours_per_week = 30
        ca1.save()
        ca2.min_hours_per_week = 30
        ca2.save()
        run_projection()
        projection = ca1.blocks.filter(date=start).aggregate(s=Sum('hours'))
        self.assertEqual(30, projection['s'])
        projection = ca2.blocks.filter(date=start).aggregate(s=Sum('hours'))
        self.assertEqual(10, projection['s'])

    def test_unallocated_hours(self):
        """ Test unallocated hours calculation """
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=40)
        unallocated_hours = ca.unallocated_hours_for_week(start)
        self.assertEqual(unallocated_hours, 40)
        ca.blocks.create(date=start, hours=5)
        unallocated_hours = ca.unallocated_hours_for_week(start)
        self.assertEqual(unallocated_hours, 35)

    def test_this_weeks_priority_type(self):
        """ Test categories for this week. """
        start = utils.get_week_start(datetime.date.today())
        end = start + datetime.timedelta(weeks=1)
        ca_starting = self._assign(start, end, hours=40)
        self.assertEqual('starting', ca_starting.this_weeks_priority_type)
        end = utils.get_week_start()
        start = end - datetime.timedelta(days=2)
        ca_ending = self._assign(start, end, hours=40)
        self.assertEqual('ending', ca_ending.this_weeks_priority_type)
        start = utils.get_week_start()
        end = start + datetime.timedelta(days=6)
        ca_starting_ending = self._assign(start, end, hours=40)
        self.assertEqual('ending', ca_starting_ending.this_weeks_priority_type)
        start = utils.get_week_start() - datetime.timedelta(days=1)
        end = start + datetime.timedelta(days=9)
        ca_ongoing = self._assign(start, end, hours=40)
        self.assertEqual('ongoing', ca_ongoing.this_weeks_priority_type)
        ## Need to test order goes ending, starting, ongoing.
        assignments = timepiece.ContractAssignment.objects.sort_by_priority()

    def test_this_weeks_allocations(self):
        # 2 weeks, 60 hours
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=20)
        person = User.objects.create_user('test2', 'a@b.com', 'abc')
        ps = self.create_person_schedule(data={'user': person})
        run_projection()
        assignments = timepiece.AssignmentAllocation.objects.during_this_week(
            self.ps.user)
        self.assertEquals(assignments.count(), 1)
        assignments = timepiece.AssignmentAllocation.objects.during_this_week(
            person)
        self.assertEquals(assignments.count(), 0)
        ca_2 = self._assign(start, end, hours=30)
        run_projection()
        assignments = timepiece.AssignmentAllocation.objects.during_this_week(
            self.ps.user)
        self.assertEquals(assignments.count(), 2)

    def test_this_weeks_hours(self):
        start = utils.get_week_start()
        end = start + datetime.timedelta(weeks=2) - datetime.timedelta(days=1)
        ca = self._assign(start, end, hours=60)
        run_projection()
        self.log_time(ca, start=start, delta=(10, 0))
        assignments = timepiece.AssignmentAllocation.objects.during_this_week(
            self.ps.user)
        self.assertEquals(assignments.count(), 1)
        assignment = assignments[0]
        self.assertEquals(assignment.hours_worked, 10)
        self.assertEquals(assignment.hours_left, assignment.hours - 10)
