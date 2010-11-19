import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.tests.base import TimepieceDataTestCase

from dateutil import relativedelta


class PayrollTest(TimepieceDataTestCase):

    def log_time(self, delta=None, billable=True, project=None):
        if delta:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        start = datetime.datetime.now()
        end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': self.contact.user,
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

