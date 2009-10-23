from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from timepiece.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from timepiece.models import Entry
from datetime import datetime, timedelta

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
        return self.client.get(reverse('timepiece-add'))

    def post_response(self, args):
        """
        Retrieve the response of a POST request with specified parameters
        """
        return self.client.post(reverse('timepiece-add'), args)

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
        #print response.content
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
