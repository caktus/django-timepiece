import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission, User
from django.test import TestCase

from timepiece import utils
from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin, LogTimeMixin

from timepiece.entries.models import Entry
from timepiece.reports.utils import find_overtime


class PayrollTest(ViewTestMixin, LogTimeMixin, TestCase):

    def setUp(self):
        super(PayrollTest, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        self.devl_activity = factories.Activity(billable=True)
        self.activity = factories.Activity()
        self.sick = factories.Project(name='sick')
        self.vacation = factories.Project(name='vacation')
        settings.TIMEPIECE_PAID_LEAVE_PROJECTS = {
            'sick': self.sick.pk, 'vacation': self.vacation.pk
        }
        self.next = utils.add_timezone(datetime.datetime(2011, 6, 1))
        self.overtime_before = utils.add_timezone(
            datetime.datetime(2011, 4, 29))
        self.first = utils.add_timezone(datetime.datetime(2011, 5, 1))
        self.first_week = utils.add_timezone(datetime.datetime(2011, 5, 2))
        self.middle = utils.add_timezone(datetime.datetime(2011, 5, 18))
        self.last_billable = utils.add_timezone(datetime.datetime(2011, 5, 28))
        self.last = utils.add_timezone(datetime.datetime(2011, 5, 31))
        self.dates = [
            self.overtime_before, self.first, self.first_week, self.middle,
            self.last, self.last_billable, self.next
        ]
        self.url = reverse('report_payroll_summary')
        self.args = {
            'year': self.first.year,
            'month': self.first.month,
        }

    def make_entry(self, user, start, delta, status='approved', billable=True,
                   project=None):
        self.log_time(start=start, delta=delta, user=user, status=status,
                      billable=billable, project=project)

    def make_logs(self, day=None, user=None, billable_project=None,
                  nonbillable_project=None):
        if not user:
            user = self.user
        if not day:
            day = self.first
        self.make_entry(user, day, (3, 30), project=billable_project)
        self.make_entry(user, day, (2, 0), project=nonbillable_project)
        self.make_entry(user, day, (5, 30), status=Entry.INVOICED, project=billable_project)
        self.make_entry(user, day, (6, 0), status=Entry.VERIFIED, project=billable_project)
        self.make_entry(user, day, (8, 0), project=self.sick)
        self.make_entry(user, day, (4, 0), project=self.vacation)

    def all_logs(self, user=None, billable_project=None,
                 nonbillable_project=None):
        if not user:
            user = self.user
        for day in self.dates:
            self.make_logs(day, user, billable_project, nonbillable_project)

    def testLastBillable(self):
        """Test the get_last_billable_day utility for validity"""
        months = range(1, 13)
        first_days = [utils.add_timezone(datetime.datetime(2011, month, 1))
                      for month in months]
        last_billable = [utils.get_last_billable_day(day).day
                         for day in first_days]
        # should equal the last saturday of every month in 2011
        self.assertEqual(last_billable,
                         [30, 27, 27, 24, 29, 26, 31, 28, 25, 30, 27, 25])

    def testFindOvertime(self):
        """Test the find_overtime utility for accuracy"""
        self.assertEqual(round(find_overtime([0, 40, 40.01, 41, 40]), 2),
                         1.01)

    def testWeeklyTotals(self):
        self.all_logs(self.user)
        self.all_logs(self.user2)
        self.login_user(self.superuser)
        response = self.client.get(self.url, self.args)
        weekly_totals = response.context['weekly_totals']
        self.assertEqual(weekly_totals[0][0][0][2], [
            Decimal('22.00'),
            Decimal('11.00'),
            '',
            Decimal('11.00'),
            Decimal('11.00'),
            '',
        ])

    def testWeeklyTotalsSameLastName(self):
        """Ensure that the totals are aggregated correctly for users with the
        same last name
        """
        User.objects.all().update(last_name='Smith')
        self.all_logs(self.user)
        self.all_logs(self.user2)
        self.login_user(self.superuser)
        response = self.client.get(self.url, self.args)
        weekly_totals = response.context['weekly_totals']
        self.assertEqual(weekly_totals[0][0][0][2], [
            Decimal('22.00'),
            Decimal('11.00'),
            '',
            Decimal('11.00'),
            Decimal('11.00'),
            '',
        ])

    def testWeeklyTotalsSameFirstLastName(self):
        """Ensure that the totals are aggregated correctly for users with the
        same last name and first name
        """
        User.objects.all().update(last_name='Smith', first_name='John')
        self.all_logs(self.user)
        self.all_logs(self.user2)
        self.login_user(self.superuser)
        response = self.client.get(self.url, self.args)
        weekly_totals = response.context['weekly_totals']
        self.assertEqual(weekly_totals[0][0][0][2], [
            Decimal('22.00'),
            Decimal('11.00'),
            '',
            Decimal('11.00'),
            Decimal('11.00'),
            '',
        ])

    def testWeeklyOvertimes(self):
        """Date_trunc on week should result in correct overtime totals"""
        dates = self.dates
        for day_num in range(28, 31):
            dates.append(utils.add_timezone(
                datetime.datetime(2011, 4, day_num)
            ))
        for day_num in range(5, 9):
            dates.append(utils.add_timezone(
                datetime.datetime(2011, 5, day_num)
            ))
        for day in dates:
            self.make_logs(day)

        def check_overtime(week0=Decimal('55.00'), week1=Decimal('55.00'),
                           overtime=Decimal('30.00')):
            self.login_user(self.superuser)
            response = self.client.get(self.url, self.args)
            weekly_totals = response.context['weekly_totals'][0][0][0][2]
            self.assertEqual(weekly_totals[0], week0)
            self.assertEqual(weekly_totals[1], week1)
            self.assertEqual(weekly_totals[5], overtime)
        check_overtime()
        # Entry on following Monday doesn't add to week1 or overtime
        self.make_logs(utils.add_timezone(datetime.datetime(2011, 5, 9)))
        check_overtime()
        # Entries in previous month before last_billable do not change overtime
        self.make_logs(utils.add_timezone(datetime.datetime(2011, 4, 24)))
        check_overtime()
        # Entry in previous month after last_billable change week0 and overtime
        self.make_logs(utils.add_timezone(
            datetime.datetime(2011, 4, 25, 1, 0)
        ))
        check_overtime(Decimal('66.00'), Decimal('55.00'), Decimal('41.00'))

    def _setupMonthlyTotals(self):
        """
        Helps set up environment for testing aspects of the monthly payroll
        summary.
        """
        self.billable_project = factories.BillableProject()
        self.nonbillable_project = factories.NonbillableProject()
        self.all_logs(self.user, self.billable_project, self.nonbillable_project)
        self.all_logs(self.user2, self.billable_project, self.nonbillable_project)
        self.login_user(self.superuser)
        self.response = self.client.get(self.url, self.args)
        self.rows = self.response.context['monthly_totals']
        self.labels = self.response.context['labels']

    def testMonthlyPayrollLabels(self):
        """
        Labels should contain all billable & nonbillable project type labels
        as well as all leave project names.
        """
        self._setupMonthlyTotals()
        self.assertEquals(
            self.labels['billable'], [self.billable_project.type.label])
        self.assertEquals(
            self.labels['nonbillable'], [self.nonbillable_project.type.label])
        self.assertEquals(len(self.labels['leave']), 2)
        self.assertTrue(self.sick.name in self.labels['leave'])
        self.assertTrue(self.vacation.name in self.labels['leave'])

    def testMonthlyPayrollRows(self):
        """Rows should contain monthly totals mapping for each user."""
        self._setupMonthlyTotals()

        # 1 row for each user, plus totals row.
        self.assertEquals(len(self.rows), 2 + 1)

        for row in self.rows[:-1]:  # Exclude totals row.
            work_total = Decimal('55.00')
            self.assertEquals(row['work_total'], work_total)

            # Last entry is summary of status.
            self.assertEquals(len(row['billable']), 1 + 1)
            for entry in row['billable']:
                self.assertEquals(entry['hours'], Decimal('45.00'))
                self.assertEquals(entry['percent'], Decimal('45.00') / work_total * 100)

            # Last entry is summary of status.
            self.assertEquals(len(row['nonbillable']), 1 + 1)
            for entry in row['nonbillable']:
                self.assertEquals(entry['hours'], Decimal('10.00'))
                self.assertEquals(entry['percent'], Decimal('10.00') / work_total * 100)

            self.assertEquals(len(row['leave']), 2 + 1)
            sick_index = self.labels['leave'].index(self.sick.name)
            vacation_index = self.labels['leave'].index(self.vacation.name)
            self.assertEquals(
                row['leave'][sick_index]['hours'], Decimal('40.00'))
            self.assertEquals(
                row['leave'][sick_index]['percent'],
                Decimal('40.00') / Decimal('60.00') * 100)
            self.assertEquals(
                row['leave'][vacation_index]['hours'], Decimal('20.00'))
            self.assertEquals(
                row['leave'][vacation_index]['percent'],
                Decimal('20.00') / Decimal('60.00') * 100)
            self.assertEquals(row['leave'][-1]['hours'], Decimal('60.00'))
            self.assertEquals(row['leave'][-1]['percent'], Decimal('100.00'))
            self.assertEquals(row['grand_total'], Decimal('115.00'))

    def testMonthlyPayrollTotals(self):
        """Last row should contain summary totals over all users."""
        self._setupMonthlyTotals()
        totals = self.rows[-1]

        work_total = Decimal('110.00')
        self.assertEquals(totals['work_total'], work_total)

        self.assertEquals(len(totals['billable']), 1 + 1)
        for entry in totals['billable']:
            self.assertEquals(entry['hours'], Decimal('90.00'))
            self.assertEquals(entry['percent'], Decimal('90.00') / work_total * 100)

        self.assertEquals(len(totals['nonbillable']), 1 + 1)
        for entry in totals['nonbillable']:
            self.assertEquals(entry['hours'], Decimal('20.00'))
            self.assertEquals(entry['percent'], Decimal('20.00') / work_total * 100)

        self.assertEquals(len(totals['leave']), 2 + 1)
        sick_index = self.labels['leave'].index(self.sick.name)
        vacation_index = self.labels['leave'].index(self.vacation.name)
        self.assertEquals(
            totals['leave'][sick_index]['hours'], Decimal('80.00'))
        self.assertEquals(
            totals['leave'][sick_index]['percent'],
            Decimal('80.00') / Decimal('120.00') * 100)
        self.assertEquals(
            totals['leave'][vacation_index]['hours'], Decimal('40.00'))
        self.assertEquals(
            totals['leave'][vacation_index]['percent'],
            Decimal('40.00') / Decimal('120.00') * 100)
        self.assertEquals(totals['leave'][-1]['hours'], Decimal('120.00'))
        self.assertEquals(totals['leave'][-1]['percent'], Decimal('100.00'))

        self.assertEquals(totals['grand_total'], Decimal('230.00'))

    def testNoPermission(self):
        """
        Regular users shouldn't be able to retrieve the payroll report
        page.
        """
        self.login_user(self.user)
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 302)

    def testSuperUserPermission(self):
        """Super users should be able to retrieve the payroll report page."""
        self.login_user(self.superuser)
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 200)

    def testPayrollPermission(self):
        """
        If a regular user is given the view_payroll_summary permission, they
        should be able to retrieve the payroll summary page.

        """
        self.login_user(self.user)
        payroll_perm = Permission.objects.get(codename='view_payroll_summary')
        self.user.user_permissions.add(payroll_perm)
        self.user.save()
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 200)
