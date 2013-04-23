import datetime

from django.conf import settings

from timepiece import utils
from timepiece.tests.base import TimepieceDataTestCase

from timepiece.reports.utils import generate_dates


class ReportsTestBase(TimepieceDataTestCase):

    def setUp(self):
        super(ReportsTestBase, self).setUp()
        self.sick = self.create_project()
        self.vacation = self.create_project()
        settings.TIMEPIECE_PAID_LEAVE_PROJECTS = {
            'sick': self.sick.pk,
            'vacation': self.vacation.pk,
        }
        self.leave = [self.sick.pk, self.vacation.pk]
        self.p1 = self.create_project(billable=True, name='1')
        self.p2 = self.create_project(billable=False, name='2')
        self.p4 = self.create_project(billable=True, name='4')
        self.p3 = self.create_project(billable=False, name='1')
        self.p5 = self.create_project(billable=True, name='3')
        self.default_projects = [self.p1, self.p2, self.p3, self.p4, self.p5]
        self.default_dates = [
            utils.add_timezone(datetime.datetime(2011, 1, 3)),
            utils.add_timezone(datetime.datetime(2011, 1, 4)),
            utils.add_timezone(datetime.datetime(2011, 1, 10)),
            utils.add_timezone(datetime.datetime(2011, 1, 16)),
            utils.add_timezone(datetime.datetime(2011, 1, 17)),
            utils.add_timezone(datetime.datetime(2011, 1, 18)),
        ]

    def make_entries(self, user=None, projects=None, dates=None,
                 hours=1, minutes=0):
        """Make several entries to help with reports tests"""
        if not user:
            user = self.user
        if not projects:
            projects = self.default_projects
        if not dates:
            dates = self.default_dates
        for project in projects:
            for day in dates:
                self.log_time(project=project, start=day,
                              delta=(hours, minutes), user=user)

    def bulk_entries(self, start=datetime.datetime(2011, 1, 2),
                   end=datetime.datetime(2011, 1, 4)):
        start = utils.add_timezone(start)
        end = utils.add_timezone(end)
        dates = generate_dates(start, end, 'day')
        projects = [self.p1, self.p2, self.p2, self.p4, self.p5, self.sick]
        self.make_entries(projects=projects, dates=dates,
                          user=self.user, hours=2)
        self.make_entries(projects=projects, dates=dates,
                          user=self.user2, hours=1)

    def check_generate_dates(self, start, end, trunc, dates):
        for index, day in enumerate(generate_dates(start, end, trunc)):
            if isinstance(day, datetime.datetime):
                day = day.date()
            self.assertEqual(day, dates[index].date())
