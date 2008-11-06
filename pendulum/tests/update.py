from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from pendulum.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from pendulum.models import Entry
from datetime import datetime, timedelta

class UpdateEntryTestCase(TestCase):
    """
    Make sure that the code for updating a closed entry works as expected.
    Rules for updating an entry:
    - Owned by user
    - Closed
    - Cannot start in the future
    - Cannot end in the future
    - Start must be before end
    """

    fixtures = ['activities', 'projects', 'users', 'entries']
    first_run = True

    def setUp(self):
        self.client = Client()

        if self.first_run:
            # try updating an entry before being logged in
            response = self.get_response(2)
            self.assertEquals(response.status_code, 302)

        # log in
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

        if self.first_run:
            # try updating an entry that doesn't exist
            response = self.get_response(1000)
            self.assertEquals(response.status_code, 302)

            self.first_run = False

    def get_response(self, id):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('pendulum-update', args=[id]))

    def post_response(self, id, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('pendulum-update', args=[id]), args)

    def testUpdateOtherUsersEntry(self):
        #--------------------------------------------------
        # 1. ENTRY THAT BELONGS TO OTHER USER
        id = 1
        now = datetime.now()

        # check to make sure that log entry isn't closed
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)

        # try to get the form to update it
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # try to manually post information
        response = self.post_response(id, {'start_time': ffd(now + timedelta(hours=-5)),
                                           'end_time': ffd(now)})
        self.assertEquals(response.status_code, 302)

        again = Entry.objects.get(pk=id)
        self.assertEquals(entry.start_time, again.start_time)
        self.assertEquals(entry.end_time, again.end_time)

    def testUpdatePausedEntry(self):
        #--------------------------------------------------
        # 2. ENTRY THAT IS PAUSED
        id = 2
        now = datetime.now()

        # get a paused entry, and make sure it's paused
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_paused)

        # try to get the form to update its information
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # try to update it with no information specified
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to update it with a little information specified
        response = self.post_response(id, {'project': 2,
                                           'comments': 'Updating the entry'})
        self.assertEquals(response.status_code, 302)

        # try to update it with all required information
        response = self.post_response(id, {'project': 1,
                                           'activity': 1,
                                           'start_time': ffd(now + timedelta(hours=-5)),
                                           'end_time': ffd(now)})
        self.assertEquals(response.status_code, 302)

        # pull back the entry, and make sure it hasn't changed
        again = Entry.objects.get(pk=id)
        self.assertEquals(entry.project, again.project)
        self.assertEquals(entry.activity, again.activity)
        self.assertEquals(entry.start_time, again.start_time)
        self.assertEquals(entry.end_time, again.end_time)
        self.assertEquals(entry.comments, again.comments)

    def testUpdateAlreadyClosedEntry(self):
        #--------------------------------------------------
        # 3. ENTRY THAT IS ALREADY CLOSED
        id = 3
        now = datetime.now()
        values = {'project': 2,
                  'activity': 2,
                  'start_time': ffd(now + timedelta(hours=-2)),
                  'end_time': ffd(now),
                  'comments': 'New comments'}

        # make sure the entry is already closed
        entry = Entry.objects.get(pk=id)
        self.assertTrue(entry.is_closed)
        self.assertFalse(entry.is_paused)

        # try to update the new entry with not enough information
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 200)

        # try various combinations of incomplete data
        response = self.post_response(id, {'project': values['project']})
        self.assertEquals(response.status_code, 200)

        response = self.post_response(id, {'project': values['project'],
                                           'activity': values['activity']})
        self.assertEquals(response.status_code, 200)

        response = self.post_response(id, {'project': values['project'],
                                           'activity': values['activity'],
                                           'start_time': values['start_time']})
        self.assertEquals(response.status_code, 200)

        response = self.post_response(id, {'activity': values['activity'],
                                           'start_time': values['start_time'],
                                           'end_time': values['end_time']})
        self.assertEquals(response.status_code, 200)

        #response = self.post_response(id, {'project': values['project'],
        #                                   'start_time': values['start_time'],
        #                                   'end_time': values['end_time']})
        #self.assertEquals(response.status_code, 200)

        response = self.post_response(id, {'project': values['project'],
                                           'activity': values['activity'],
                                           'end_time': values['end_time']})
        self.assertEquals(response.status_code, 200)

        # update the entry with new information
        response = self.post_response(id, values)
        self.assertEquals(response.status_code, 302)

        # make sure the information is just as I want it to be
        entry = Entry.objects.get(pk=id)
        self.assertEquals(entry.project.id, values['project'])
        self.assertEquals(entry.activity.id, values['activity'])
        self.assertEquals(ffd(entry.start_time), values['start_time'])
        self.assertEquals(ffd(entry.end_time), values['end_time'])
        self.assertEquals(entry.comments, values['comments'])

    def testUpdateOpenUnpausedEntry(self):
        #--------------------------------------------------
        # 4. ENTRY THAT IS OPEN AND NOT PAUSED
        id = 4
        now = datetime.now()

        # get an open entry, and make sure it's not paused
        entry = Entry.objects.get(pk=id)
        self.assertFalse(entry.is_closed)
        self.assertFalse(entry.is_paused)

        # try to get the form to update its information
        response = self.get_response(id)
        self.assertEquals(response.status_code, 302)

        # try to update it with no information specified
        response = self.post_response(id, {})
        self.assertEquals(response.status_code, 302)

        # try to update it with a little information specified
        response = self.post_response(id, {'project': 2,
                                           'comments': 'Updating the entry'})
        self.assertEquals(response.status_code, 302)

        # try to update it with all required information
        response = self.post_response(id, {'project': 1,
                                           'activity': 1,
                                           'start_time': ffd(now + timedelta(hours=-5)),
                                           'end_time': ffd(now)})
        self.assertEquals(response.status_code, 302)

        # pull back the entry, and make sure it hasn't changed
        again = Entry.objects.get(pk=id)
        self.assertEquals(entry.project, again.project)
        self.assertEquals(entry.activity, again.activity)
        self.assertEquals(entry.start_time, again.start_time)
        self.assertEquals(entry.end_time, again.end_time)
        self.assertEquals(entry.comments, again.comments)

        # now update it again, just to make sure
        values = {'project': 1,
                  'activity': 1,
                  'start_time': ffd(now + timedelta(hours=-2)),
                  'end_time': ffd(now + timedelta(hours=-1)),
                  'comments': 'New comments'}
        response = self.post_response(id, values)
        self.assertEquals(response.status_code, 302)

        # pull back the entry, and make sure it has changed
        again = Entry.objects.get(pk=id)
        self.assertNotEquals(again.project.id, values['project'])
        self.assertNotEquals(again.activity.id, values['activity'])
        self.assertNotEquals(again.start_time, values['start_time'])
        self.assertNotEquals(again.end_time, values['end_time'])
        self.assertNotEquals(again.comments, values['comments'])

    def testSetStartInFuture(self):
        """
        Try to update a good, closed entry to start and end in the future
        """
        id = 3
        now = datetime.now()
        values = {'project': 2,
                  'activity': 2,
                  'start_time': ffd(now + timedelta(hours=2)),
                  'end_time': ffd(now + timedelta(hours=5)),
                  'comments': 'New comments'}

        response = self.post_response(id, values)
        self.assertEquals(response.status_code, 200)

        # make sure the information is still as in the fixture
        entry = Entry.objects.get(pk=id)
        self.assertNotEquals(entry.project.id, values['project'])
        self.assertNotEquals(entry.activity.id, values['activity'])
        self.assertNotEquals(ffd(entry.start_time), values['start_time'])
        self.assertNotEquals(ffd(entry.end_time), values['end_time'])
        self.assertNotEquals(entry.comments, values['comments'])

    def testSetEndInFuture(self):
        """
        Try to update a good, closed entry to end in the future
        """
        id = 3
        now = datetime.now()
        values = {'project': 2,
                  'activity': 2,
                  'start_time': ffd(now + timedelta(hours=-2)),
                  'end_time': ffd(now + timedelta(hours=1)),
                  'comments': 'New comments'}

        response = self.post_response(id, values)
        self.assertEquals(response.status_code, 200)

        # make sure the information is still as in the fixture
        entry = Entry.objects.get(pk=id)
        self.assertNotEquals(entry.project.id, values['project'])
        self.assertNotEquals(entry.activity.id, values['activity'])
        self.assertNotEquals(ffd(entry.start_time), values['start_time'])
        self.assertNotEquals(ffd(entry.end_time), values['end_time'])
        self.assertNotEquals(entry.comments, values['comments'])

    def testSetStartAfterEnd(self):
        """
        Try to update a good, closed entry to start after it ends
        """
        id = 3
        now = datetime.now()
        values = {'project': 2,
                  'activity': 2,
                  'start_time': ffd(now + timedelta(hours=2)),
                  'end_time': ffd(now),
                  'comments': 'New comments'}

        response = self.post_response(id, values)
        self.assertEquals(response.status_code, 200)

        # make sure the information is still as in the fixture
        entry = Entry.objects.get(pk=id)
        self.assertNotEquals(entry.project.id, values['project'])
        self.assertNotEquals(entry.activity.id, values['activity'])
        self.assertNotEquals(ffd(entry.start_time), values['start_time'])
        self.assertNotEquals(ffd(entry.end_time), values['end_time'])
        self.assertNotEquals(entry.comments, values['comments'])
