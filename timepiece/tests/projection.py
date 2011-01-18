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

from timepiece.projection import run_projection, contact_weekly_assignments
from timepiece import utils


class ProjectionTest(TimepieceDataTestCase):

    def setUp(self):
        user = User.objects.create_user('test', 'a@b.com', 'abc')
        person = self.create_person({'user': user})
        self.ps = self.create_person_schedule(data={'contact': person})

    def log_time(self, assignment, delta=None, start=None):
        if delta:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = datetime.datetime.now()
        elif not isinstance(start, datetime.datetime):
            raise Exception('start must be a datetime object')
        end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': assignment.contact.user,
                'start_time': start,
                'end_time': end,
                'project': assignment.contract.project}
        return self.create_entry(data)

    def test_week_start(self):
        """ Test that all days Sunday through Saturday return Sunday """
        sunday = datetime.date(2011, 1, 16)
        self.assertEqual(sunday, utils.get_week_start(sunday))
        monday = datetime.date(2011, 1, 17)
        self.assertEqual(sunday, utils.get_week_start(monday))
        saturday = datetime.date(2011, 1, 22)
        self.assertEqual(sunday, utils.get_week_start(saturday))

    def test_generate_weeks(self):
        """ Test generation of full week ranges """
        # 2 weeks
        start = datetime.date(2011, 1, 16)
        end = datetime.date(2011, 1, 29)
        weeks = utils.generate_weeks(start=start, end=end)
        self.assertEqual(2, weeks.count())
        # 3 weeks
        start = datetime.date(2011, 1, 16)
        end = datetime.date(2011, 1, 30)
        weeks = utils.generate_weeks(start=start, end=end)
        self.assertEqual(3, weeks.count())
        # random weeks
        num = random.randint(5, 20)
        start = utils.get_week_start(datetime.date.today())
        end = start + datetime.timedelta(weeks=num - 1)
        weeks = utils.generate_weeks(start=start, end=end)
        self.assertEqual(num, weeks.count())

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
        hours = 30
        pc = self.create_project_contract({'num_hours': hours})
        ca = self.create_contract_assignment({'contract': pc,
                                              'contact': self.ps.contact,
                                              'num_hours': hours})
        hours_per_week = hours/pc.weeks_remaining.count()
        self.assertEqual(hours_per_week, ca.weekly_commitment)

    def test_weekly_commmitment_with_hours_worked(self):
        """ Test weekly commitment with previously logged hours """
        hours = 30
        start = datetime.datetime.today() - datetime.timedelta(weeks=1)
        end = start + datetime.timedelta(weeks=2)
        pc = self.create_project_contract({'num_hours': hours,
                                           'start_date': start,
                                           'end_date': end})
        ca = self.create_contract_assignment({'contract': pc,
                                              'contact': self.ps.contact,
                                              'num_hours': hours})
        self.log_time(ca, start=start, delta=(10, 0))
        self.assertEqual(10, ca.hours_worked)
        self.assertEqual(20, ca.hours_remaining)
        self.assertEqual(10, ca.weekly_commitment)

    def _assign(self, start=None, end=None, hours=30):
        pc = self.create_project_contract({'num_hours': hours,
                                           'start_date': start,
                                           'end_date': end})
        ca = self.create_contract_assignment({'contract': pc,
                                              'contact': self.ps.contact,
                                              'num_hours': hours})
        return ca

    def test_contact_weekly_assignment_left_bound(self):
        start = datetime.datetime.today() - datetime.timedelta(weeks=1)
        end = start + datetime.timedelta(weeks=2)
        ca = self._assign(start, end)
        for schedule, week, assignments in contact_weekly_assignments():
            self.assertTrue(assignments.filter(pk=ca.pk).exists())

    def test_contact_weekly_assignment_right_bound(self):
        start = datetime.datetime.today() + datetime.timedelta(weeks=1)
        end = start + datetime.timedelta(weeks=2)
        ca = self._assign(start, end)
        for schedule, week, assignments in contact_weekly_assignments():
            self.assertTrue(assignments.filter(pk=ca.pk).exists())

    def testSingleAssignmentProjection(self):
        start = datetime.datetime.today() - datetime.timedelta(weeks=1)
        end = start + datetime.timedelta(weeks=2)
        ca = self._assign(start, end, hours=60)
        run_projection()
        self.assertEqual(60, ca.blocks.aggregate(s=Sum('hours'))['s'])

