import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.tests.base import TimepieceDataTestCase

from dateutil import relativedelta


class PayrollTest(TimepieceDataTestCase):

    def log_time(self, delta=None, billable=True, project=None, start=None):
        if delta:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = datetime.datetime.now()
        end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': self.contact,
                'start_time': start,
                'end_time': end,
                'billable': billable}
        if project:
            data['project'] = project
        return self.create_entry(data)

    def testPersonSummary(self):
        sick = self.create_project()
        vacation = self.create_project()
        settings.TIMEPIECE_PROJECTS = {'sick': sick.pk, 'vacation': vacation.pk}
        rp = self.create_person_repeat_period({'contact': self.contact})
        start = datetime.date.today().replace(day=1)
        end = start + relativedelta.relativedelta(months=1)
        billable = self.log_time(delta=(3, 30))
        non_billable = self.log_time(delta=(2, 0), billable=False)
        sick = self.log_time(delta=(8, 0), project=sick)
        vacation = self.log_time(delta=(4, 0), project=vacation)
        summary = rp.summary(start, end)
        self.assertEqual(summary['billable'], Decimal('3.50'))
        self.assertEqual(summary['non_billable'], Decimal('2.00'))
        self.assertEqual(summary['sick'], Decimal('8.00'))
        self.assertEqual(summary['vacation'], Decimal('4.00'))
        self.assertEqual(summary['total'], Decimal('17.50'))

    def testWeeklyHours(self):
        """ Test basic functionality of hours worked per week """
        rp = self.create_person_repeat_period({'contact': self.contact})
        p1 = self.create_project()
        start = datetime.datetime(2011, 1, 3)
        self.log_time(project=p1, start=start, delta=(8, 0))
        start = datetime.datetime(2011, 1, 8)
        self.log_time(project=p1, start=start, delta=(8, 0))
        self.assertEqual(rp.hours_in_week(start), Decimal('16.00'))

    def testWeeklyHoursBounds(self):
        """ Make sure hours worked on Sunday's don't overlap weekly hours """
        rp = self.create_person_repeat_period({'contact': self.contact})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(8, 0))
        start2 = datetime.datetime(2011, 1, 9)
        self.log_time(project=p1, start=start2, delta=(8, 0))
        self.assertEqual(rp.hours_in_week(start1), Decimal('8.00'))
        self.assertEqual(rp.hours_in_week(start2), Decimal('8.00'))

    def testWeeklyOvertimeHours(self):
        """ Test weekly overtime calculation """
        rp = self.create_person_repeat_period({'contact': self.contact})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(44, 0))
        self.assertEqual(rp.overtime_hours_in_week(start1), Decimal('4.00'))

    def testWeeklyNonOvertimeHours(self):
        """ Test weekly overtime calculation """
        rp = self.create_person_repeat_period({'contact': self.contact})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(40, 0))
        self.assertEqual(rp.overtime_hours_in_week(start1), Decimal('0.00'))

    def testMonthlyOvertimeHours(self):
        """ Test monthly overtime calculation """
        rp = self.create_person_repeat_period({'contact': self.contact})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(44, 0))
        start1 = datetime.datetime(2011, 1, 9)
        self.log_time(project=p1, start=start1, delta=(44, 0))
        self.assertEqual(rp.total_monthly_overtime(start1), Decimal('8.00'))

