from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

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
