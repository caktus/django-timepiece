import datetime
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece.templatetags.timepiece_tags import get_active_hours
from timepiece.tests.base import TimepieceDataTestCase


class DashboardTestCase(TimepieceDataTestCase):
    def setUp(self):
        super(DashboardTestCase, self).setUp()
        self.unpriveleged_user = User.objects.create_user(
            username='tester',
            password='abc',
            email='email@email.com'
        )
        self.url = reverse('timepiece-entries')
        self.text = [u'Clock In', u'Add Entry', u'My Active Entries']
        self.now = timezone.now()

    def test_unpriveleged_user(self):
        """
        A regular user should not be able to see what people are
        working on or timesheet related links
        """
        self.client.login(username='tester', password='abc')

        response = self.client.get(self.url)
        for text in self.text:
            self.assertNotContains(response, text)

    def test_timepiece_user(self):
        """
        A timepiece user should be able to see what others are
        working on as well as timesheet links
        """
        self.client.login(username='user', password='abc')

        response = self.client.get(self.url)
        for text in self.text:
            self.assertContains(response, text)

    def test_work_this_week(self):
        """
        Entries, including the active one, should show up
        in the Work This Week table.
        """
        self.create_entry({
            'start_time': self.now,
            'end_time': self.now + datetime.timedelta(hours=1),
        })
        entry = self.create_entry({
            'start_time': self.now + datetime.timedelta(hours=2),
            'project': self.create_project(billable=True)
        })
        hours = get_active_hours(entry)
        total_hours = Decimal('%.2f' % 1.0) + hours

        self.client.login(username='user', password='abc')

        response = self.client.get(self.url)
        context = response.context
        self.assertEquals(context['current_total'], total_hours)

    def test_time_detail(self):
        """
        An active entry should not appear in the Time
        Detail This Week table
        """
        entry = self.create_entry({
            'start_time': self.now,
            'end_time': self.now + datetime.timedelta(hours=1),
        })
        self.create_entry({
            'start_time': self.now + datetime.timedelta(hours=2),
            'project': self.create_project(billable=True)
        })

        self.client.login(username='user', password='abc')

        response = self.client.get(self.url)
        context = response.context
        self.assertEquals(len(context['this_weeks_entries']), 1)
        self.assertEquals(context['this_weeks_entries'][0], entry)
