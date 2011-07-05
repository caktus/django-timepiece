from django.test import Client

from timepiece.tests.base import TimepieceDataTestCase

from django.core.urlresolvers import reverse


class EditSettingsTest(TimepieceDataTestCase):
    
    def setUp(self):
        super(EditSettingsTest, self).setUp()
        self.client = Client()
        self.url = reverse('edit_settings')
        self.client.login(username='user', password='abc')
        
    def test_success_next(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        response = self.client.post(self.url, { 
            'first_name': 'Michael',
            'last_name': 'Clemmons',
            'email': 'test@caktusgroup.com',
        })
        self.assertRedirects(response, reverse('timepiece-entries'))
        next = reverse('timepiece-clock-in')
        next_query_url = '%s?next=%s' % (self.url, next)
        response = self.client.post(next_query_url, { 
            'first_name': 'Michael',
            'last_name': 'Clemmons',
            'email': 'test@caktusgroup.com',
        })
        self.assertRedirects(response, next)

