from django.test import TestCase
from django.core.urlresolvers import reverse

from timepiece.tests.base import TimepieceDataTestCase


class QuickSearchTest(TimepieceDataTestCase):
    def setUp(self):
        super(QuickSearchTest, self).setUp()

    def testUserSearch(self):
        """
        Test that you are redirected to the correct profile
        """
        self.client.login(username='superuser', password='abc')

        url = reverse('quick_search')

        response = self.client.get(url, data={
            'quick_search_0': '%s' % self.superuser.get_full_name(),
            'quick_search_1': 'individual-%d' % self.superuser.pk
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['person'].username, 'superuser')

        # quick_search_0 can be anything (an artifact of django-selectable?)
        response = self.client.get(url, data={
            'quick_search_0': None,
            'quick_search_1': 'individual-%d' % self.superuser.pk
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['person'].username, 'superuser')

    def testMalformedUserSearch(self):
        """
        Test that the correct value error is thrown
        """
        self.client.login(username='superuser', password='abc')

        url = reverse('quick_search')

        response = self.client.get(url, data={
            'quick_search_0': '%s' % self.superuser.get_full_name(),
            'quick_search_1': 'individual'
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertEquals(form.errors['quick_search'],
            ['User, business, or project does not exist'])

        response = self.client.get(url, data={
            'quick_search_0': '%s' % self.superuser.get_full_name(),
            'quick_search_1': ''
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertEquals(form.errors['quick_search'],
            ['User, business, or project does not exist'])

        response = self.client.get(url, data={
            'quick_search_0': '%s' % self.superuser.get_full_name(),
            'quick_search_1': '-%d' % self.superuser.pk
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertEquals(form.errors['quick_search'],
            ['User, business, or project does not exist'])

        response = self.client.get(url, data={
            'quick_search_0': '%s' % self.superuser.get_full_name(),
            'quick_search_1': '-'
        }, follow=True)

        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertEquals(form.errors['quick_search'],
            ['User, business, or project does not exist'])
