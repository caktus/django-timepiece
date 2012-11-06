from dateutil.parser import parse as dt_parse
import datetime

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece.tests.base import TimepieceDataTestCase
from timepiece import utils


class DashboardTestCase(TimepieceDataTestCase):

    def setUp(self):
        super(DashboardTestCase, self).setUp()
        self.unpriveleged_user = self.create_user('tester', 'email@email.com',
                'abc')
        self.url = reverse('dashboard')
        self.text = [u'Clock In', u'Add Entry', u'My Active Entries']
        self.now = timezone.now()
        self.start = self.now.replace(hour=8, minute=0, second=0)
        self.yesterday = self.start - datetime.timedelta(days=1)
        self.tomorrow = self.start + datetime.timedelta(days=1)
        self.client.login(username='user', password='abc')

    def dt_near(self, dt_a, dt_b, tolerance=10):
        return abs(utils.get_total_seconds(dt_a - dt_b)) < tolerance

    def test_current_entry(self):
        """
        Assure the response contains 'active_entry' when it exists.
        """
        entry_start = self.start.replace(hour=0)
        active_entry = self.create_entry({'start_time': entry_start})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_entry'], active_entry)

    def test_current_entry_not_today(self):
        """
        Assure response contains 'active_entry' when it exists.
        """
        active_entry = self.create_entry({'start_time': self.yesterday})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_entry'], active_entry)

    def test_no_current_entry(self):
        """
        Assure 'active_entry' is None when no active entry exists
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_entry'], None)

#    def test_unpriveleged_user(self):
#        """
#        A regular user should not be able to see what people are
#        working on or timesheet related links
#        """
#        self.client.login(username='tester', password='abc')

#        response = self.client.get(self.url)
#        for text in self.text:
#            self.assertNotContains(response, text)

#    def test_timepiece_user(self):
#        """
#        A timepiece user should be able to see what others are
#        working on as well as timesheet links
#        """
#        self.client.login(username='user', password='abc')

#        response = self.client.get(self.url)
#        for text in self.text:
#            self.assertContains(response, text)
