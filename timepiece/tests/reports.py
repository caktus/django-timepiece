import datetime
from dateutil import relativedelta

from django.core.urlresolvers import reverse

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece import utils


class TestHourlyReport(TimepieceDataTestCase):
    def setUp(self):
        super(TestHourlyReport, self).setUp()
        self.p1 = self.create_project(billable=True, name='1')
        self.p2 = self.create_project(billable=False, name='2')
        self.p4 = self.create_project(billable=True, name='4')
        self.p3 = self.create_project(billable=False, name='1')
        self.client.login(username='user', password='abc')
        self.get_args = []
        self.url = reverse('hourly_report', args=self.get_args)

    def make_entries(self):
        """Make several entries to help with reports tests"""
        self.client.login(username='user', password='abc')
        projects = [
            self.p1, self.p2, self.p3, self.p4
        ]
        days = [
                datetime.datetime(2011, 1, 3),
                datetime.datetime(2011, 1, 4),
                datetime.datetime(2011, 1, 10),
                datetime.datetime(2011, 1, 16),
                datetime.datetime(2011, 1, 17),
                datetime.datetime(2011, 1, 18)
        ]
        for day in days:
            for project in projects:
                self.log_time(project=project, start=day, delta=(1, 0))

    def date_headers(self, start, end, trunc):
        return utils.generate_dates(start, end, trunc)

    def generate_dates(self, start, end, trunc, dates):
        for index, day in enumerate(self.date_headers(start, end, trunc)):
            self.assertEqual(day, dates[index])

    def testGenerateMonths(self):
        dates = [datetime.datetime(2011, month, 1) for month in xrange(1, 13)]
        start = datetime.datetime(2011, 1, 1)
        end = datetime.datetime(2011, 12, 1)
        self.generate_dates(start, end, 'month', dates)

    def testGenerateWeeks(self):
        dates = [
            datetime.datetime(2010, 12, 27),
            datetime.datetime(2011, 01, 03),
            datetime.datetime(2011, 01, 10),
            datetime.datetime(2011, 01, 17),
            datetime.datetime(2011, 01, 24),
            datetime.datetime(2011, 01, 31),
        ]
        start = datetime.datetime(2011, 1, 1)
        end = datetime.datetime(2011, 2, 1)
        self.generate_dates(start, end, 'week', dates)

    def testGenerateDays(self):
        dates = [datetime.datetime(2011, 1, day) for day in xrange(1, 32)]
        start = datetime.datetime(2011, 1, 1)
        end = datetime.datetime(2011, 1, 31)
        self.generate_dates(start, end, 'day', dates)
        
    def testTruncs(self):
        self.make_entries()
        #TODO: test date_trunc model manager
