from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from timepiece.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from timepiece.models import Entry

class ClockOutTestCase(TestCase):
    """
    Make sure that entries can be closed properly.
    Rules for clocking out:
    - Entry must belong to user
    - Entry must be open
    - Entry may be paused, but must be unpaused after being closed
    """

    fixtures = ['activities', 'projects', 'users', 'entries']
    first_run = True

    def setUp(self):
        self.client = Client()

        if self.first_run:
            # try closing an entry before being logged in
            response = self.get_response(2)
            self.assertEquals(response.status_code, 302)

        # log in
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

        if self.first_run:
            # try closing an entry that doesn't exist
            response = self.get_response(1000)
            self.assertEquals(response.status_code, 302)

            self.first_run = False

    def get_response(self, id):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('timepiece-clock-out', args=[id]))

    def post_response(self, id, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('timepiece-clock-out', args=[id]), args)

    def testCloseOtherUsersEntry(self):
        #--------------------------------------------------
        # 1. ENTRY THAT BELONGS TO OTHER USER
        id = 1

        # check to make sure that log entry isn't closed
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)

        # try closing an entry that doesn't belong to the user
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # try to close without posting any information
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to close posting no activity
        response = self.post_response(id, {'comments': "closing the entry"})
        self.assertEquals(response.status_code, 302)

        # try to close posting minimal information
        response = self.post_response(id, {'activity': 1})
        self.assertEquals(response.status_code, 302)

        # make sure the entry is still open
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)

    def testClosePausedEntry(self):
        #--------------------------------------------------
        # 2. ENTRY THAT IS PAUSED
        id = 2

        # check to make sure that log entry isn't closed
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_paused)
        self.assertFalse(entry.is_closed)

        # try closing an entry that is paused
        response = self.get_response(id)
        self.assertEquals(response.status_code, 200)

        # try to close without posting any information
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to close posting no activity
        response = self.post_response(id, {'comments': "closing the entry"})
        self.assertEquals(response.status_code, 302)

        # try to close posting minimal information
        response = self.post_response(id, {'activity': 1})
        self.assertEquals(response.status_code, 302)

        # make sure the entry is still open
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)

    def testCloseAlreadyClosedEntry(self):
        #--------------------------------------------------
        # 3. ENTRY THAT IS ALREADY CLOSED
        id = 3

        # check to make sure that log entry is closed
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)

        # try closing an entry that is closed
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # try to close without posting any information
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to close posting no activity
        response = self.post_response(id, {'comments': "closing the entry"})
        self.assertEquals(response.status_code, 302)

        # try to close posting minimal information
        response = self.post_response(id, {'activity': 1})
        self.assertEquals(response.status_code, 302)

        # make sure the entry is still closed
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)

    def testCloseOpenUnpausedEntry(self):
        #--------------------------------------------------
        # 4. ENTRY THAT IS OPEN AND NOT PAUSED
        id = 4

        # check to make sure that log entry isn't closed
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_paused)
        self.assertFalse(entry.is_closed)

        # try closing an entry that is not paused
        response = self.get_response(id)
        self.assertEquals(response.status_code, 200)

        # try to close without posting any information
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to close posting no activity
        response = self.post_response(id, {'comments': "closing the entry"})
        self.assertEquals(response.status_code, 302)

        # try to close posting minimal information
        response = self.post_response(id, {'activity': 1})
        self.assertEquals(response.status_code, 302)

        # make sure the entry is still open
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)
