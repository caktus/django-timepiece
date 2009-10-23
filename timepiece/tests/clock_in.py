from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from timepiece.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from timepiece.models import Entry

class ClockInTestCase(TestCase):
    """
    Check to make sure the code for clocking in works properly.
    Rules for clocking in:
    - User must be logged in
    - An active project must be provided
    """

    fixtures = ['activities', 'projects', 'users', 'entries']

    def setUp(self):
        self.client = Client()

    def get_response(self):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('timepiece-clock-in'))

    def post_response(self, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('timepiece-clock-in'), args)

    def testClockIn(self):
        clock_in_url = reverse('timepiece-clock-in')

        # try simply getting to the clock in page, where you choose a project
        # should redirect to the login page
        response = self.get_response()
        self.assertEquals(response.status_code, 302)

        # unauthorized access, try to login with invalid user
        response = self.client.login(username='invaliduser', password='invalid')
        self.assertFalse(response)

        # now try to login with an inactive account
        response = self.client.login(username='inactiveuser', password=VALID_PASSWORD)
        self.assertFalse(response)

        # try to login with valid username and invalid password
        response = self.client.login(username=VALID_USER, password='invalid')
        self.assertFalse(response)

        # now try to login with a valid username and password
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

        # after a successful login, try to get the page where you choose the
        # project
        response = self.get_response()
        self.assertEquals(response.status_code, 200)

        # now try clocking in without having selected a project
        response = self.post_response({})
        self.assertEquals(response.status_code, 200)

        # try to clock in to a project that is inactive
        response = self.post_response({'project': 3})
        self.assertEquals(response.status_code, 200)

        # and finally clocking in with a project selected
        response = self.post_response({'project': 1})
        self.assertEquals(response.status_code, 302)

        # make sure that there is at least one log entry
        entries = Entry.objects.current()
        self.assertTrue(len(entries) >= 1)
