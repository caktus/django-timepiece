import datetime

from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission

from timepiece.tests.base import TimepieceDataTestCase

class TestGeneralLedger(TimepieceDataTestCase):
    def setUp(self):
        super(TestGeneralLedger, self).setUp()
        self.url = reverse('timepiece-summary')

    def testNoPermission(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def testSuperUserPermission(self):
        self.client.login(username='superuser', password='abc')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def testEntrySummaryPermission(self):
        self.client.login(username='user', password='abc')
	entry_summary_permission = Permission.objects.get(codename='view_entry_summary')
        self.user.user_permissions.add(entry_summary_permission)
	self.user.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
