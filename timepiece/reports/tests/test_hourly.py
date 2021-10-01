import datetime
from decimal import Decimal
from random import randint

from django.contrib.auth.models import Permission
from django.db.models import Q
from django.utils import timezone

from timepiece import utils

from timepiece.entries.models import Entry
from timepiece.reports.tests.base import ReportsTestBase
from timepiece.reports.utils import get_project_totals, generate_dates
from timepiece.tests.base import ViewTestMixin, LogTimeMixin


class TestHourlyReport(ViewTestMixin, LogTimeMixin, ReportsTestBase):
    url_name = 'report_hourly'

    def test_generate_months(self):
        dates = [utils.add_timezone(datetime.datetime(2011, month, 1))
                 for month in range(1, 13)]
        start = datetime.date(2011, 1, 1)
        end = datetime.date(2011, 12, 1)
        self.check_generate_dates(start, end, 'month', dates)

    def test_generate_weeks(self):
        dates = [
            utils.add_timezone(datetime.datetime(2010, 12, 27)),
            utils.add_timezone(datetime.datetime(2011, 1, 3)),
            utils.add_timezone(datetime.datetime(2011, 1, 10)),
            utils.add_timezone(datetime.datetime(2011, 1, 17)),
            utils.add_timezone(datetime.datetime(2011, 1, 24)),
            utils.add_timezone(datetime.datetime(2011, 1, 31)),
        ]
        start = utils.add_timezone(datetime.datetime(2011, 1, 1))
        end = utils.add_timezone(datetime.datetime(2011, 2, 1))
        self.check_generate_dates(start, end, 'week', dates)

    def test_generate_days(self):
        dates = [utils.add_timezone(datetime.datetime(2011, 1, day))
                 for day in range(1, 32)]
        start = utils.add_timezone(datetime.datetime(2011, 1, 1))
        end = utils.add_timezone(datetime.datetime(2011, 1, 31))
        self.check_generate_dates(start, end, 'day', dates)

    def check_truncs(self, trunc, billable, non_billable):
        self.make_entries(user=self.user)
        self.make_entries(user=self.user2)
        entries = Entry.objects.date_trunc(trunc)
        for entry in entries:
            if entry['billable']:
                self.assertEqual(entry['hours'], billable)
            else:
                self.assertEqual(entry['hours'], non_billable)

    def test_trunc_month(self):
        self.check_truncs('month', 18, 12)

    def test_trunc_week(self):
        self.check_truncs('week', 6, 4)

    def test_trunc_day(self):
        self.check_truncs('day', 3, 2)

    def get_project_totals(self, date_headers, trunc, query=Q(),
                           hour_type='total'):
        """Helper function for testing project_totals utility directly"""
        entries = Entry.objects.date_trunc(trunc).filter(query)
        if entries:
            pj_totals = get_project_totals(entries, date_headers, hour_type)
            pj_totals = list(pj_totals)
            rows = pj_totals[0][0]
            hours = [hours for name, user_id, hours in rows]
            totals = pj_totals[0][1]
            return hours, totals
        else:
            return ''

    def log_daily(self, start, day2, end):
        self.log_time(project=self.p1, start=start, delta=(1, 0))
        self.log_time(project=self.p1, start=day2, delta=(0, 30))
        self.log_time(project=self.p3, start=day2, delta=(1, 0))
        self.log_time(project=self.p1, start=day2, delta=(3, 0),
                      user=self.user2)
        self.log_time(project=self.sick, start=end, delta=(2, 0),
                      user=self.user2)

    def test_daily_total(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1))
        day2 = utils.add_timezone(datetime.datetime(2011, 1, 2))
        end = utils.add_timezone(datetime.datetime(2011, 1, 3))
        self.log_daily(start, day2, end)
        trunc = 'day'
        date_headers = generate_dates(start, end, trunc)
        pj_totals = self.get_project_totals(date_headers, trunc)
        self.assertEqual(pj_totals[0][0],
                         [Decimal('1.00'), Decimal('1.50'), ''])
        self.assertEqual(pj_totals[0][1],
                         ['', Decimal('3.00'), Decimal('2.00')])
        self.assertEqual(pj_totals[1],
                         [Decimal('1.00'), Decimal('4.50'), Decimal('2.00')])

    def test_billable_nonbillable(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1))
        day2 = utils.add_timezone(datetime.datetime(2011, 1, 2))
        end = utils.add_timezone(datetime.datetime(2011, 1, 3))
        self.log_daily(start, day2, end)
        trunc = 'day'
        billableQ = Q(project__type__billable=True)
        non_billableQ = Q(project__type__billable=False)
        date_headers = generate_dates(start, end, trunc)
        pj_billable = self.get_project_totals(date_headers, trunc, Q(),
                                              'billable')
        pj_billable_q = self.get_project_totals(date_headers, trunc, billableQ,
                                                'total')
        pj_non_billable = self.get_project_totals(date_headers, trunc, Q(),
                                                  'non_billable')
        pj_non_billable_q = self.get_project_totals(date_headers, trunc,
                                                    non_billableQ, 'total')
        self.assertEqual(list(pj_billable), list(pj_billable_q))
        self.assertEqual(list(pj_non_billable), list(pj_non_billable_q))

    def test_weekly_total(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 3))
        end = utils.add_timezone(datetime.datetime(2011, 1, 6))
        self.bulk_entries(start, end)
        trunc = 'week'
        date_headers = generate_dates(start, end, trunc)
        pj_totals = self.get_project_totals(date_headers, trunc)
        self.assertEqual(pj_totals[0][0], [48])
        self.assertEqual(pj_totals[0][1], [24])
        self.assertEqual(pj_totals[1], [72])

    def test_monthly_total(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1))
        end = utils.add_timezone(datetime.datetime(2011, 3, 1))
        trunc = 'month'
        last_day = randint(5, 10)
        worked1 = randint(1, 3)
        worked2 = randint(1, 3)
        for month in range(1, 7):
            for day in range(1, last_day + 1):
                day = utils.add_timezone(datetime.datetime(2011, month, day))
                self.log_time(start=day, delta=(worked1, 0), user=self.user)
                self.log_time(start=day, delta=(worked2, 0), user=self.user2)
        date_headers = generate_dates(start, end, trunc)
        pj_totals = self.get_project_totals(date_headers, trunc)
        for hour in pj_totals[0][0]:
            self.assertEqual(hour, last_day * worked1)
        for hour in pj_totals[0][1]:
            self.assertEqual(hour, last_day * worked2)

    def args_helper(self, **kwargs):
        start = utils.add_timezone(kwargs.pop('start', datetime.datetime(2011, 1, 2)))
        end = utils.add_timezone(kwargs.pop('end', datetime.datetime(2011, 1, 4)))
        defaults = {
            'from_date': start.strftime('%Y-%m-%d'),
            'to_date': end.strftime('%Y-%m-%d'),
            'export_users': True,
            'billable': True,
            'non_billable': True,
            'paid_leave': True,
            'trunc': 'week',
        }
        defaults.update(kwargs)
        return defaults

    def make_totals(self, args={}):
        """Return CSV from hourly report for verification in tests"""
        self.login_user(self.superuser)
        response = self._get(data=args, follow=True)
        return [item.split(',')
                for item in response.content.decode('utf-8').split('\r\n')][:-1]

    def check_totals(self, args, data):
        """assert that project_totals contains the data passed in"""
        totals = self.make_totals(args)
        for row, datum in zip(totals, data):
            self.assertEqual(row[1:], datum)

    def test_form_type__none(self):
        """When no types are checked, no results should be returned."""
        self.bulk_entries()
        args = {'billable': False, 'non_billable': False, 'paid_leave': False}
        args = self.args_helper(**args)
        data = []
        self.check_totals(args, data)

    def test_form_type__all(self):
        """When all types are checked, no filtering should occur."""
        self.bulk_entries()
        args = {'billable': True, 'non_billable': True, 'paid_leave': True}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['12.00000', '24.00000', '36.00000'],
            ['6.00000', '12.00000', '18.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__exclude_billable(self):
        """Non-billable or leave entries should be included."""
        self.bulk_entries()
        args = {'billable': False, 'non_billable': True, 'paid_leave': True}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['6.00000', '12.00000', '18.00000'],
            ['3.00000', '6.00000', '9.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__exclude_nonbillable(self):
        """Billable or leave entries should be included."""
        self.bulk_entries()
        args = {'billable': True, 'non_billable': False, 'paid_leave': True}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['8.00000', '16.00000', '24.00000'],
            ['4.00000', '8.00000', '12.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__exclude_leave(self):
        """No leave entries should be included."""
        self.bulk_entries()
        args = {'billable': True, 'non_billable': True, 'paid_leave': False}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['10.00000', '20.00000', '30.00000'],
            ['5.00000', '10.00000', '15.00000'],
            ['15.00000', '30.00000', '45.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__only_billable(self):
        """Billable, non-leave entries should be included."""
        self.bulk_entries()
        args = {'billable': True, 'non_billable': False, 'paid_leave': False}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['6.00000', '12.00000', '18.00000'],
            ['3.00000', '6.00000', '9.00000'],
            ['9.00000', '18.00000', '27.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__only_nonbillable(self):
        """Non-billable, non-leave entries should be included."""
        self.bulk_entries()
        args = {'billable': False, 'non_billable': True, 'paid_leave': False}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['4.00000', '8.00000', '12.00000'],
            ['2.00000', '4.00000', '6.00000'],
            ['6.00000', '12.00000', '18.00000'],
        ]
        self.check_totals(args, data)

    def test_form_type__only_leave(self):
        """Only leave entries should be included."""
        self.bulk_entries()
        args = {'billable': False, 'non_billable': False, 'paid_leave': True}
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['2.00000', '4.00000', '6.00000'],
            ['1.00000', '2.00000', '3.00000'],
        ]
        self.check_totals(args, data)

    def test_form_day(self):
        """Hours should be totaled for each day in the date range."""
        args = {
            'billable': True,
            'non_billable': False,
            'paid_leave': False,
            'trunc': 'day',
        }
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', '01/04/2011', 'Total'],
            ['6.00000', '6.00000', '6.00000', '18.00000'],
            ['3.00000', '3.00000', '3.00000', '9.00000'],
            ['9.00000', '9.00000', '9.00000', '27.00000'],
        ]
        self.bulk_entries()
        self.check_totals(args, data)

    def test_form_week(self):
        """Hours should be totaled for each week in the date range."""
        args = {
            'billable': True,
            'non_billable': True,
            'paid_leave': True,
            'trunc': 'week',
        }
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', 'Total'],
            ['12.00000', '24.00000', '36.00000'],
            ['6.00000', '12.00000', '18.00000'],
            ['18.00000', '36.00000', '54.00000'],
        ]
        self.bulk_entries()
        self.check_totals(args, data)

    def test_form_month(self):
        """Hours should be totaled for each month in the date range."""
        tz = timezone.get_current_timezone()
        start = datetime.datetime(2011, 1, 4, tzinfo=tz)
        end = datetime.datetime(2011, 3, 28, tzinfo=tz)
        args = {
            'billable': True,
            'non_billable': False,
            'paid_leave': False,
            'trunc': 'month',
        }
        args = self.args_helper(start=start, end=end, **args)
        data = [
            ['01/04/2011', '02/01/2011', '03/01/2011', 'Total'],
            ['168.00000', '168.00000', '168.00000', '504.00000'],
            ['84.00000', '84.00000', '84.00000', '252.00000'],
            ['252.00000', '252.00000', '252.00000', '756.00000'],
        ]
        self.bulk_entries(start, end)
        self.check_totals(args, data)

    def test_form_projects(self):
        """Filter hours for specific projects."""
        # Test project 1
        self.bulk_entries()
        args = {
            'billable': True,
            'non_billable': True,
            'paid_leave': False,
            'trunc': 'day',
            'projects_1': self.p1.id,
        }
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', '01/04/2011', 'Total'],
            ['2.00000', '2.00000', '2.00000', '6.00000'],
            ['1.00000', '1.00000', '1.00000', '3.00000'],
            ['3.00000', '3.00000', '3.00000', '9.00000'],
        ]
        self.check_totals(args, data)

        # Test with project 2
        args = {
            'billable': True,
            'non_billable': True,
            'paid_leave': False,
            'trunc': 'day',
            'projects_1': self.p2.id,
        }
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', '01/04/2011', 'Total'],
            ['4.00000', '4.00000', '4.00000', '12.00000'],
            ['2.00000', '2.00000', '2.00000', '6.00000'],
            ['6.00000', '6.00000', '6.00000', '18.00000'],
        ]
        self.check_totals(args, data)

        # Test with 2 project filters
        args = {
            'billable': True,
            'non_billable': True,
            'paid_leave': False,
            'trunc': 'day',
            'projects_1': [self.p2.id, self.p4.id],
        }
        args = self.args_helper(**args)
        data = [
            ['01/02/2011', '01/03/2011', '01/04/2011', 'Total'],
            ['6.00000', '6.00000', '6.00000', '18.00000'],
            ['3.00000', '3.00000', '3.00000', '9.00000'],
            ['9.00000', '9.00000', '9.00000', '27.00000'],
        ]
        self.check_totals(args, data)

    def test_no_permission(self):
        """view_entry_summary permission is required to view this report."""
        self.login_user(self.user)
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def test_entry_summary_permission(self):
        """view_entry_summary permission is required to view this report."""
        self.login_user(self.user)
        entry_summ_perm = Permission.objects.get(codename='view_entry_summary')
        self.user.user_permissions.add(entry_summ_perm)
        self.user.save()
        response = self._get()
        self.assertEqual(response.status_code, 200)
