from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase


class BusinessTest(TimepieceDataTestCase):
    def setUp(self):
        self.client.login(username='user', password='abc')
        self.url = reverse('create_business')
        self.data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def login_with_permission(self):
        user = User.objects.create_user('admin', 'e@e.com', 'abc')
        perm = Permission.objects.get(codename='add_business')
        user.user_permissions.add(perm)
        self.client.login(username='admin', password='abc')

    def test_user_create_business(self):
        """A regular user shouldnt be able to create a business"""
        response = self.client.get(self.url)
        # They should be redirected to the login page
        self.assertEquals(response.status_code, 302)

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(timepiece.Business.objects.count(), 0)

    def test_user_create_business_permission(self):
        """A user with permissions should be able to create a business"""
        self.login_with_permission()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response,
            'timepiece/business/create_edit.html')

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(timepiece.Business.objects.count(), 1)
