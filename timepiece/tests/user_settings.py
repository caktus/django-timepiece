from django.test import Client
from django.core.urlresolvers import reverse

from django.contrib.auth import models as auth_models

from timepiece import models as timepiece
from timepiece import forms
from timepiece.tests.base import TimepieceDataTestCase


class EditSettingsTest(TimepieceDataTestCase):
    def setUp(self):
        super(EditSettingsTest, self).setUp()
        self.client = Client()
        self.url = reverse('edit_settings')
        self.client.login(username='user', password='abc')
        self.activities = []
        for i in range(0, 5):
            self.activities.append(self.create_activity())

    def edit_profile(self, url, data):
        response = self.client.post(url, data)
        return response

    def test_success_next(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        data = {
            'first_name': 'Michael',
            'last_name': 'Clemmons',
            'email': 'test@caktusgroup.com',
        }
        response = self.edit_profile(self.url, data)
        self.assertRedirects(response, reverse('timepiece-entries'))
        self.user = auth_models.User.objects.get(pk=self.user.pk)
        for k, v in data.iteritems():
            value = getattr(self.user, k)
            self.assertEquals(value, v)
        next = reverse('timepiece-clock-in')
        next_query_url = '%s?next=%s' % (self.url, next)
        data = {
            'first_name': 'Terry',
            'last_name': 'Pratchet',
            'email': 'test@caktusgroup.com',
        }
        response = self.edit_profile(next_query_url, data)
        self.assertRedirects(response, next)
        self.profile = timepiece.UserProfile.objects.get(user=self.user)
