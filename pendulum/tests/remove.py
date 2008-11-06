from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from pendulum.tests.utils import VALID_PASSWORD, VALID_USER, ffd
from pendulum.models import Entry

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
