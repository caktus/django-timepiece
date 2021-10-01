import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.test import TestCase

from timepiece import utils
from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin, LogTimeMixin

from ..models import Project


class TestProjectTimesheet(ViewTestMixin, LogTimeMixin, TestCase):
    url_name = 'view_project_timesheet'

    def setUp(self):
        super(TestProjectTimesheet, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        self.p1 = factories.BillableProject(name='1')
        self.p2 = factories.NonbillableProject(name='2')
        self.p4 = factories.BillableProject(name='4')
        self.p3 = factories.NonbillableProject(name='1')
        self.url_args = (self.p1.pk,)
        self.devl_activity = factories.Activity(billable=True)
        self.activity = factories.Activity()

    def make_entries(self):
        days = [
            utils.add_timezone(datetime.datetime(2011, 1, 1)),
            utils.add_timezone(datetime.datetime(2011, 1, 28)),
            utils.add_timezone(datetime.datetime(2011, 1, 31)),
            utils.add_timezone(datetime.datetime(2011, 2, 1)),
            timezone.now(),
        ]
        self.log_time(project=self.p1, start=days[0], delta=(1, 0))
        self.log_time(project=self.p2, start=days[0], delta=(1, 0))
        self.log_time(project=self.p1, start=days[1], delta=(1, 0))
        self.log_time(project=self.p3, start=days[1], delta=(1, 0))
        self.log_time(project=self.p1, user=self.user2, start=days[2],
                      delta=(1, 0))
        self.log_time(project=self.p2, start=days[2], delta=(1, 0))
        self.log_time(project=self.p1, start=days[3], delta=(1, 0))
        self.log_time(project=self.p3, start=days[3], delta=(1, 0))
        self.log_time(project=self.p1, start=days[4], delta=(1, 0))
        self.log_time(project=self.p2, start=days[4], delta=(1, 0))

    def testNoPermission(self):
        self.login_user(self.user)
        self.make_entries()
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def testNoProject(self):
        Project.objects.all().delete()
        self.login_user(self.superuser)
        response = self._get(url_args=(999,))
        self.assertEqual(response.status_code, 404)

    def testEmptyProjectTimesheet(self):
        """
        The project timesheet should be empty if there are no entries, or a
        month has been selected for which there are no entries
        """
        self.login_user(self.superuser)

        def verify_empty(response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'], self.p1)
            self.assertEqual(list(response.context['entries']), [])
        response = self._get()
        verify_empty(response)
        self.make_entries()
        data = {
            'year': 2011,
            'month': 4,
        }
        response = self._get(data=data)
        verify_empty(response)

    def testCurrentProjectTimesheet(self):
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p1)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(Decimal(response.context['total']), Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(Decimal(user_entry['sum']), Decimal(1))

    def testOldProjectTimesheet(self):
        self.login_user(self.superuser)
        self.make_entries()
        data = {
            'year': 2011,
            'month': 1,
        }
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p1)
        self.assertEqual(len(response.context['entries']), 3)
        self.assertEqual(Decimal(response.context['total']), Decimal(3))
        user_entry0 = response.context['user_entries'][0]
        user_entry1 = response.context['user_entries'][1]
        self.assertEqual(user_entry0['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry0['user__first_name'], self.user.first_name)
        self.assertEqual(Decimal(user_entry0['sum']), Decimal(2))
        self.assertEqual(user_entry1['user__last_name'], self.user2.last_name)
        self.assertEqual(user_entry1['user__first_name'],
                         self.user2.first_name)
        self.assertEqual(Decimal(user_entry1['sum']), Decimal(1))

    def testOtherProjectTimesheet(self):
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get(url_args=(self.p2.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p2)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(Decimal(response.context['total']), Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(Decimal(user_entry['sum']), Decimal(1))

    def test_project_csv(self):
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get(
            url_name='view_project_timesheet_csv', url_args=(self.p1.pk,))
        self.assertEqual(response.status_code, 200)
        data = dict(response.items())
        self.assertEqual(data['Content-Type'], 'text/csv')
        disposition = data['Content-Disposition']
        self.assertTrue(disposition.startswith('attachment; filename='))
        contents = response.content.decode('utf-8').splitlines()
        headers = contents[0].split(',')
        # Assure user's comments are not included.
        self.assertTrue('comments' not in headers)

    def testRoundingConversions(self):
        """
        Verify that entries (which are in seconds) approximate a correct hourly value
        once each decimal conversion per entry is summed.
        """
        xtime = timezone.now() - relativedelta(minutes=10)
        factories.Entry(**{
            'user': self.superuser,
            'project': self.p2,
            'start_time': xtime,
            'end_time': xtime + relativedelta(seconds=29)
        })
        factories.Entry(**{
            'user': self.superuser,
            'project': self.p2,
            'start_time': xtime + relativedelta(seconds=30),
            'end_time': xtime + relativedelta(seconds=60)
        })

        self.login_user(self.superuser)
        response = self._get(url_args=(self.p2.pk,))
        entries = response.context['entries']
        self.assertEqual(len(entries), 2)
        self.assertAlmostEqual(sum(Decimal(e['hours']) for e in entries), Decimal(0.016), places=2)
