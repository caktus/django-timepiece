from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from pendulum.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from pendulum.models import Entry

class PauseTestCase(TestCase):
    """
    Check to make sure that entries can be paused and unpaused as expected.
    Rules for pausing an entry:
    - Must be owned by user
    - If paused, unpause it
    - Entry must be open
    """

    fixtures = ['activities', 'projects', 'users', 'entries']
    first_run = True

    def setUp(self):
        self.client = Client()

        if self.first_run:
            # try pausing an entry before being logged in
            response = self.get_response(2)
            self.assertEquals(response.status_code, 302)

        # log in
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

        if self.first_run:
            # try pausing an entry that doesn't exist
            response = self.get_response(1000)
            self.assertEquals(response.status_code, 302)

            self.first_run = False

    def get_response(self, id):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('pendulum-toggle-paused', args=[id]))

    def testPauseOtherUsersEntry(self):
        #--------------------------------------------------
        # 1. ENTRY THAT BELONGS TO OTHER USER
        id = 1

        # check to make sure that log entry isn't paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_paused)

        # try pausing an entry that doesn't belong to the current user
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # check to make sure that log entry still isn't paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_paused)

    def testAlreadyPausedEntry(self):
        #--------------------------------------------------
        # 2. ENTRY THAT IS ALREADY PAUSED
        id = 2

        # check to make sure that log entry is paused
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_paused)

        # try pausing an already paused entry
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # check to make sure that log entry is no longer paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_paused)

    def testAlreadyClosedEntry(self):
        #--------------------------------------------------
        # 3. ENTRY THAT IS ALREADY CLOSED
        id = 3

        # check to make sure that log entry is closed and not paused
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)

        # try pausing an already closed entry
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # check to make sure that log entry is still closed and not paused
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)

    def testOpenUnpausedEntry(self):
        #--------------------------------------------------
        # 4. ENTRY THAT IS OPEN AND NOT PAUSED
        id = 4

        # check to make sure that log entry is open and not paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)
        self.assertFalse(entry.is_paused)

        # try pausing an open entry owned by the user
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # make sure the entry is still open but now paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)
        self.assertTrue(entry.is_paused)
