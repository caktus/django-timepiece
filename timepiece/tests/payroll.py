import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse

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
        self.next = datetime.datetime(2011, 6, 1)
        self.overtime_before = datetime.datetime(2011, 4, 29)
        self.first = datetime.datetime(2011, 5, 1)
        self.first_week = datetime.datetime(2011, 5, 2)
        self.middle = datetime.datetime(2011, 5, 18)
        self.last_billable = datetime.datetime(2011, 5, 28)
        self.last = datetime.datetime(2011, 5, 31)
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

    def make_logs(self, day=None, user=None):
        if not user:
            user = self.user
        if not day:
            day = self.first
        billable = self.make_entry(user, day, (3, 30))
        non_billable = self.make_entry(user, day, (2, 0), billable=False)
        invoiced = self.make_entry(user, day, (5, 30), status='invoiced')
        unapproved = self.make_entry(user, day, (6, 0), status='verified')
        sick = self.make_entry(user, day, (8, 0), project=self.sick)
        vacation = self.make_entry(user, day, (4, 0), project=self.vacation)

    def all_logs(self, user=None):
        if not user:
            user = self.user
        for day in self.dates:
            self.make_logs(day, user)

    def testLastBillable(self):
        """Test the get_last_billable_day utility for validity"""
        months = range(1, 13)
        first_days = [datetime.datetime(2011, month, 1) for month in months]
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
        desc, totals = utils.format_leave(leave)
        self.assertEqual(desc[0], (u'vacation', Decimal('4.00')))
        self.assertEqual(desc[1], (u'sick', Decimal('8.00')))
        self.assertEqual(totals, Decimal('12.00'))

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
        self.all_logs()
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
            dates.append(datetime.datetime(2011, 4, day_num))
        for day_num in xrange(5, 9):
            dates.append(datetime.datetime(2011, 5, day_num))
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
        self.make_logs(datetime.datetime(2011, 5, 9))
        check_overtime()
        #Entries in previous month before last_billable do not change overtime
        self.make_logs(datetime.datetime(2011, 4, 24))
        check_overtime()
        #Entry in previous month after last_billable change week0 and overtime
        self.make_logs(datetime.datetime(2011, 4, 25, 1, 0))
        check_overtime(Decimal('66.00'), Decimal('55.00'), Decimal('41.00'))

    def testMonthlyTotals(self):
        self.all_logs()
        self.all_logs(self.user2)
        self.client.login(username='superuser', password='abc')
        response = self.client.get(self.url, self.args)
        monthly_totals = response.context['monthly_totals']
        self.assertEqual(monthly_totals[0][1],
                         [(Decimal('45.00'), 81.82),
                          (Decimal('10.00'), 18.18),
                          Decimal('55.00')
                         ])
        self.assertEqual(monthly_totals[0][2],
                         [(u'vacation', Decimal('20.00')),
                          (u'sick', Decimal('40.00'))])
        self.assertEqual(monthly_totals[0][3], Decimal('115.00'))
