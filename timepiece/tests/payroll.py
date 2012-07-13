import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece import utils
from timepiece.tests.base import TimepieceDataTestCase

from dateutil.relativedelta import relativedelta


class PayrollTest(TimepieceDataTestCase):

    def setUp(self):
        super(PayrollTest, self).setUp()
        self.sick = self.create_project(name='sick')
        self.vacation = self.create_project(name='vacation')
        settings.TIMEPIECE_PROJECTS = {
            'sick': self.sick.pk, 'vacation': self.vacation.pk
        }
        tz = timezone.get_current_timezone()
        self.next = datetime.datetime(2011, 6, 1, tzinfo=tz)
        self.overtime_before = datetime.datetime(2011, 4, 29, tzinfo=tz)
        self.first = datetime.datetime(2011, 5, 1, tzinfo=tz)
        self.first_week = datetime.datetime(2011, 5, 2, tzinfo=tz)
        self.middle = datetime.datetime(2011, 5, 18, tzinfo=tz)
        self.last_billable = datetime.datetime(2011, 5, 28, tzinfo=tz)
        self.last = datetime.datetime(2011, 5, 31, tzinfo=tz)
        self.dates = [
            self.overtime_before, self.first, self.first_week, self.middle,
            self.last, self.last_billable, self.next
        ]
        self.url = reverse('payroll_summary')
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
        billable = self.make_entry(user, day, (3, 30),
                project=billable_project)
        non_billable = self.make_entry(user, day, (2, 0),
                project=nonbillable_project)
        invoiced = self.make_entry(user, day, (5, 30), status='invoiced',
                project=billable_project)
        unapproved = self.make_entry(user, day, (6, 0), status='verified',
                project=billable_project)
        sick = self.make_entry(user, day, (8, 0), project=self.sick)
        vacation = self.make_entry(user, day, (4, 0), project=self.vacation)

    def all_logs(self, user=None, billable_project=None,
            nonbillable_project=None):
        if not user:
            user = self.user
        for day in self.dates:
            self.make_logs(day, user, billable_project, nonbillable_project)

    def testLastBillable(self):
        """Test the get_last_billable_day utility for validity"""
        months = range(1, 13)
        first_days = [timezone.make_aware(datetime.datetime(2011, month, 1), \
            timezone.get_current_timezone()) for month in months]
        last_billable = [utils.get_last_billable_day(day).day \
                         for day in first_days]
        #should equal the last saturday of every month in 2011
        self.assertEqual(last_billable,
                         [30, 27, 27, 24, 29, 26, 31, 28, 25, 30, 27, 25])

    def testFindOvertime(self):
        """Test the find_overtime utility for accuracy"""
        self.assertEqual(round(utils.find_overtime([0, 40, 40.01, 41, 40]), 2),
                         1.01)

    def testFormatLeave(self):
        """
        format_leave formats leave time to (list of descriptions, total hours)
        """
        self.make_logs()
        projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
        leave = timepiece.Entry.objects.filter(project__in=projects.values())
        leave = leave.values('user', 'hours', 'project__name')
        desc, total = utils.format_leave(leave)
        self.assertEqual(desc[u'vacation'], Decimal('4.00'))
        self.assertEqual(desc[u'sick'], Decimal('8.00'))
        self.assertEqual(len(desc), 2)
        self.assertEqual(total, Decimal('12.00'))

    def testGetHourSummaries(self):
        """
        Given dictionaries of hours, return the format for payroll summary
        """
        hours_dict1 = {'total': 9.00, 'billable': 6.00, 'non_billable': 3.00}
        self.assertEqual(utils.get_hour_summaries(hours_dict1),
                         [(6.0, 66.67), (3.0, 33.33), 9.0])
        hours_dict2 = {'total': 0.00, 'billable': 0.00, 'non_billable': 0.00}
        self.assertEqual(utils.get_hour_summaries(hours_dict2),
                         [(0, 0), (0, 0), 0])
        #Double check that division by zero doesn't occur.
        hours_dict3 = {'total': 0.00, 'billable': 6.00, 'non_billable': 3.00}
        self.assertEqual(utils.get_hour_summaries(hours_dict3),
                         [(0, 0), (0, 0), 0.0])

    def testWeeklyTotals(self):
        self.all_logs(self.user)
        self.all_logs(self.user2)
        self.client.login(username='superuser', password='abc')
        response = self.client.get(self.url, self.args)
        weekly_totals = response.context['weekly_totals']
        self.assertEqual(weekly_totals[0][0][0][1],
                         [Decimal('22.00'),
                          Decimal('11.00'), '',
                          Decimal('11.00'),
                          Decimal('11.00'), ''
                         ])

    def testWeeklyOvertimes(self):
        """Date_trunc on week should result in correct overtime totals"""
        dates = self.dates
        for day_num in xrange(28, 31):
            dates.append(timezone.make_aware(
                datetime.datetime(2011, 4, day_num),
                timezone.get_current_timezone()
            ))
        for day_num in xrange(5, 9):
            dates.append(timezone.make_aware(
                datetime.datetime(2011, 5, day_num),
                timezone.get_current_timezone()
            ))
        for day in dates:
            self.make_logs(day)

        def check_overtime(week0=Decimal('55.00'), week1=Decimal('55.00'),
                           overtime=Decimal('30.00')):
            self.client.login(username='superuser', password='abc')
            response = self.client.get(self.url, self.args)
            weekly_totals = response.context['weekly_totals'][0][0][0][1]
            self.assertEqual(weekly_totals[0], week0)
            self.assertEqual(weekly_totals[1], week1)
            self.assertEqual(weekly_totals[5], overtime)
        check_overtime()
        #Entry on following Monday doesn't add to week1 or overtime
        self.make_logs(timezone.make_aware(
            datetime.datetime(2011, 5, 9),
            timezone.get_current_timezone(),
        ))
        check_overtime()
        #Entries in previous month before last_billable do not change overtime
        self.make_logs(timezone.make_aware(
            datetime.datetime(2011, 4, 24),
            timezone.get_current_timezone(),
        ))
        check_overtime()
        #Entry in previous month after last_billable change week0 and overtime
        self.make_logs(timezone.make_aware(
            datetime.datetime(2011, 4, 25, 1, 0),
            timezone.get_current_timezone(),
        ))
        check_overtime(Decimal('66.00'), Decimal('55.00'), Decimal('41.00'))

    def testMonthlyTotals(self):
        """Test correctness of monthly totals in payroll summary view.
            labels: maps {'billable_status': [project_type_label]}
            rows: a list of maps of monthly totals to user.
            totals: the last row should be a map of sum totals of all users.
        """
        billable_project = self.create_project(name="Billable", billable=True)
        nonbillable_project = self.create_project(name="Nonbillable",
                billable=False)
        self.all_logs(self.user, billable_project, nonbillable_project)
        self.all_logs(self.user2, billable_project, nonbillable_project)
        self.client.login(username='superuser', password='abc')
        response = self.client.get(self.url, self.args)
        rows = response.context['monthly_totals']
        labels = response.context['labels']

        # Labels should contain all billable & nonbillable project type labels.
        self.assertEquals(labels['billable'], [billable_project.type.label])
        self.assertEquals(labels['nonbillable'],
                [nonbillable_project.type.label])

        # Rows should contain monthly totals mapping for each user.
        self.assertEquals(len(rows), 2 + 1)  # 1 for each user, plus totals
        for row in rows[:-1]:
            self.assertEquals(row['billable'][0]['hours'], Decimal('45.00'))
            self.assertEquals(row['billable'][0]['percent'],
                    Decimal('45.00') / Decimal('55.00') * 100)
            self.assertEquals(row['billable'][1]['hours'], Decimal('45.00'))
            self.assertEquals(row['billable'][1]['percent'],
                    Decimal('45.00') / Decimal('55.00') * 100)

            self.assertEquals(row['nonbillable'][0]['hours'], Decimal('10.00'))
            self.assertEquals(row['nonbillable'][0]['percent'],
                    Decimal('10.00') / Decimal('55.00') * 100)
            self.assertEquals(row['nonbillable'][1]['hours'], Decimal('10.00'))
            self.assertEquals(row['nonbillable'][1]['percent'],
                    Decimal('10.00') / Decimal('55.00') * 100)

            self.assertEquals(row['work_total'], Decimal('55.00'))
            self.assertEquals(row['leave']['hours']['sick'], Decimal('40.00'))
            self.assertEquals(row['leave']['hours']['vacation'],
                    Decimal('20.00'))
            self.assertEquals(row['leave']['total'], Decimal('60.00'))
            self.assertEquals(row['grand_total'], Decimal('115.00'))

        # Last row should contain summary totals over all users.
        totals = rows[-1]
        self.assertEquals(totals['billable'][0]['hours'], Decimal('90.00'))
        self.assertEquals(totals['billable'][0]['percent'],
                Decimal('90.00') / Decimal('110.00') * 100)
        self.assertEquals(totals['billable'][1]['hours'], Decimal('90.00'))
        self.assertEquals(totals['billable'][1]['percent'],
                Decimal('90.00') / Decimal('110.00') * 100)

        self.assertEquals(totals['nonbillable'][0]['hours'], Decimal('20.00'))
        self.assertEquals(totals['nonbillable'][0]['percent'],
                Decimal('20.00') / Decimal('110.00') * 100)
        self.assertEquals(totals['nonbillable'][1]['hours'], Decimal('20.00'))
        self.assertEquals(totals['nonbillable'][1]['percent'],
                Decimal('20.00') / Decimal('110.00') * 100)

        self.assertEquals(totals['work_total'], Decimal('110.00'))
        self.assertEquals(totals['leave']['hours']['sick'], Decimal('80.00'))
        self.assertEquals(totals['leave']['hours']['vacation'],
                Decimal('40.00'))
        self.assertEquals(totals['leave']['total'], Decimal('120.00'))
        self.assertEquals(totals['grand_total'], Decimal('230.00'))

    def testNoPermission(self):
        """
        Regular users shouldn't be able to retrieve the payroll report
        page.

        """
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 302)

    def testSuperUserPermission(self):
        """Super users should be able to retrieve the payroll report page."""
        self.client.login(username='superuser', password='abc')
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 200)

    def testPayrollPermission(self):
        """
        If a regular user is given the view_payroll_summary permission, they
        should be able to retrieve the payroll summary page.

        """
        self.client.login(username='user', password='abc')
        payroll_perm = Permission.objects.get(codename='view_payroll_summary')
        self.user.user_permissions.add(payroll_perm)
        self.user.save()
        response = self.client.get(self.url, self.args)
        self.assertEqual(response.status_code, 200)
