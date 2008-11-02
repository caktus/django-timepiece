"""
This is a set of unit tests to make sure the timeclock application works
after making "improvements" or modifications to the code.
"""

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from pendulum.utils import determine_period
from pendulum.models import Entry, Project, Activity
from datetime import datetime, timedelta

VALID_USER, VALID_PASSWORD = 'testuser', 'password'

def ffd(date):
    """
    Form-friendly date formatter
    """
    return date.strftime('%Y-%m-%d %H:%M')

class DetermineDatesTestCase(TestCase):
    """
    Make sure the period date boundary function is working properly.  Currently
    the range calculator will go from the first day of the month to the last
    day of the same month.  Eventually, this should test for configurable
    period lengths.
    """

    fixtures = ['activities', 'projects', 'users', 'entries']

    def setUp(self):
        self.client = Client()

    def testDeterminePeriod(self):
        # try some dates
        dates_to_try = (
            datetime(2005, 12, 13), datetime(2006, 4, 12),
            datetime(2006, 7, 19),  datetime(2007, 1, 9),
            datetime(2007, 5, 21),  datetime(2007, 6, 10),
            datetime(2007, 6, 26),  datetime(2007, 7, 2),
            datetime(2007, 7, 31),  datetime(2007, 9, 6),
            datetime(2007, 12, 2),  datetime(2008, 1, 30),
            datetime(2008, 2, 27),  datetime(2008, 6, 6),
        )

        expected_results = [
            (datetime(2005, 12, 1), datetime(2005, 12, 31)),    # 13 dec 05
            (datetime(2006, 4, 1), datetime(2006, 4, 30)),      # 12 apr 06
            (datetime(2006, 7, 1), datetime(2006, 7, 31)),      # 19 jul 06
            (datetime(2007, 1, 1), datetime(2007, 1, 31)),      # 9 jan 07
            (datetime(2007, 5, 1), datetime(2007, 5, 31)),      # 21 may 07
            (datetime(2007, 6, 1), datetime(2007, 6, 30)),      # 10 jun 07
            (datetime(2007, 6, 1), datetime(2007, 6, 30)),      # 26 jun 07
            (datetime(2007, 7, 1), datetime(2007, 7, 31)),      # 2 jul 07
            (datetime(2007, 7, 1), datetime(2007, 7, 31)),      # 31 jul 07
            (datetime(2007, 9, 1), datetime(2007, 9, 30)),      # 6 sept 07
            (datetime(2007, 12, 1), datetime(2007, 12, 31)),    # 2 dec 07
            (datetime(2008, 1, 1), datetime(2008, 1, 31)),      # 30 jan 08
            (datetime(2008, 2, 1), datetime(2008, 2, 29)),      # 27 feb 08
            (datetime(2008, 6, 1), datetime(2008, 6, 30)),      # 6 jun 08
        ]

        count = 0
        for date in dates_to_try:
            start, end = determine_period(date)

            exp_s, exp_e = expected_results[count]

            # make sure the resulting start date matches the expected value
            self.assertEquals(start.year, exp_s.year)
            self.assertEquals(start.month, exp_s.month)
            self.assertEquals(start.day, exp_s.day)

            # make sure the resulting end date matches the expected value
            self.assertEquals(end.year, exp_e.year)
            self.assertEquals(end.month, exp_e.month)
            self.assertEquals(end.day, exp_e.day)

            # increment the counter so we can get the correct expected results
            count += 1

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
        return self.client.get(reverse('pendulum-clock-in'))

    def post_response(self, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('pendulum-clock-in'), args)

    def testClockIn(self):
        clock_in_url = reverse('pendulum-clock-in')

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
        return self.client.get(reverse('pendulum-clock-out', args=[id]))

    def post_response(self, id, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('pendulum-clock-out', args=[id]), args)

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

class AddEntryTestCase(TestCase):
    """
    Rules for adding an entry:
    - User is logged in
    - Project is specified
    - Start time is in the past
    - End time is in the past
    - Start time is before end time
    """

    fixtures = ['activities', 'projects', 'users', 'entries']
    first_run = True

    def setUp(self):
        self.client = Client()

        if self.first_run:
            # try adding an entry before being logged in
            response = self.get_response()
            self.assertEquals(response.status_code, 302)

            self.first_run = False

        # log in
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

    def get_response(self):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('pendulum-add'))

    def post_response(self, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('pendulum-add'), args)

    def testAddEntryForm(self):
        # try to get the add log form
        response = self.get_response()
        self.assertEquals(response.status_code, 200)

    def testAddBlankEntry(self):
        start_count = Entry.objects.all().count()

        # try to create an entry with no information
        response = self.post_response({})
        self.assertEquals(response.status_code, 200)

        # just make sure that no entries were actually added
        end_count = Entry.objects.all().count()
        self.assertEquals(start_count, end_count)

    def testAddNotEnoughInfoEntry(self):
        start_count = Entry.objects.all().count()

        # try adding an entry without enough information
        response = self.post_response({'comments': 'Adding a new entry'})
        self.assertEquals(response.status_code, 200)

        # try adding an entry with a bit more information
        response = self.post_response({'project': 1,
                                       'comments': 'Adding a new entry'
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with a bit more information
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'comments': 'Adding a new entry'
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with a bit more information
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': datetime(2008, 4, 30, 21, 00),
                                       'comments': 'Adding a new entry'
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with a bit more information
        response = self.post_response({'activity': 1,
                                       'start_time': datetime(2008, 4, 30, 21, 00),
                                       'end_time': datetime(2008, 4, 30, 22, 00),
                                       'comments': 'Adding a new entry'
                                      })
        self.assertEquals(response.status_code, 200)

        ## try adding an entry with a bit more information
        #response = self.post_response({'project': 1,
        #                               'start_time': datetime(2008, 4, 30, 21, 00),
        #                               'end_time': datetime(2008, 4, 30, 22, 00),
        #                               'comments': 'Adding a new entry'
        #                              })
        #self.assertEquals(response.status_code, 302)

        # try adding an entry with a bit more information
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'end_time': datetime(2008, 4, 30, 22, 00),
                                       'comments': 'Adding a new entry'
                                      })
        self.assertEquals(response.status_code, 200)

        # just make sure that no entries were actually added
        end_count = Entry.objects.all().count()
        self.assertEquals(start_count, end_count)

    def testAddJustEnoughEntry(self):
        now = datetime.now()
        start_count = Entry.objects.all().count()

        # try adding an entry with just enough information
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now + timedelta(hours=-5)),
                                       'end_time': ffd(now)
                                      })
        self.assertEquals(response.status_code, 302)

        # just make sure that no entries were actually added
        end_count = Entry.objects.all().count()
        self.assertEquals(start_count + 1, end_count)

    def testAddAllInfoEntry(self):
        now = datetime.now()
        start_count = Entry.objects.all().count()

        # try adding an entry with just enough information
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now + timedelta(hours=-5)),
                                       'end_time': ffd(now),
                                       'comments': 'A new entry!'
                                      })
        self.assertEquals(response.status_code, 302)

        # just make sure that no entries were actually added
        end_count = Entry.objects.all().count()
        self.assertEquals(start_count + 1, end_count)

    def testAddWithInvalidDates(self):
        now = datetime.now()
        start_count = Entry.objects.all().count()

        # try adding an entry with a start time in the future
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now + timedelta(days=5)),
                                       'end_time': ffd(now + timedelta(days=5, hours=1))
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with an end time in the future
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now),
                                       'end_time': ffd(now + timedelta(hours=5))
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with a start time after the end time
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now + timedelta(hours=5)),
                                       'end_time': ffd(now)
                                      })
        self.assertEquals(response.status_code, 200)

        # try adding an entry with the same start and end time
        response = self.post_response({'project': 1,
                                       'activity': 1,
                                       'start_time': ffd(now),
                                       'end_time': ffd(now)
                                      })
        self.assertEquals(response.status_code, 200)

        # just make sure that no entries were actually added
        end_count = Entry.objects.all().count()
        self.assertEquals(start_count, end_count)

class RemoveEntryTestCase(TestCase):
    """
    Test the functionality for removing an entry
    Rules for removal:
    - Owned by user
    - The user will be prompted to confirm their decision
    """

    fixtures = ['activities', 'projects', 'users', 'entries']

    def setUp(self):
        self.client = Client()

        # try removing an entry before being logged in
        response = self.get_response(4)
        self.assertEquals(response.status_code, 302)

        # log in
        response = self.client.login(username=VALID_USER, password=VALID_PASSWORD)
        self.assertTrue(response)

        # try removing an entry that does not exist
        response = self.get_response(1000)
        self.assertEquals(response.status_code, 302)

    def get_response(self, id):
        """
        Retrieve the response of a GET request
        """
        return self.client.get(reverse('pendulum-delete', args=[id]))

    def post_response(self, id, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('pendulum-delete', args=[id]), args)

    def testRemoveOtherUsersEntry(self):
        #--------------------------------------------------
        # 1. ENTRY THAT BELONGS TO ANOTHER USER
        self.performWithIdAndCodes(1, 302, 302)

    def testRemoveClosedEntry(self):
        #--------------------------------------------------
        # 2. ENTRY THAT IS CLOSED
        self.performWithIdAndCodes(2, 200, 302)

    def testRemovePausedEntry(self):
        #--------------------------------------------------
        # 3. ENTRY THAT IS PAUSED
        self.performWithIdAndCodes(3, 200, 302)

    def testRemoveOpenEntry(self):
        #--------------------------------------------------
        # 4. ENTRY THAT IS OPEN
        self.performWithIdAndCodes(4, 200, 302)

    def performWithIdAndCodes(self, id, get, post):
        entry = Entry.objects.get(pk=id)
        self.assertEquals(self.get_response(id).status_code, get)
        self.assertEquals(self.post_response(id, {'key': entry.delete_key}).status_code, post)
