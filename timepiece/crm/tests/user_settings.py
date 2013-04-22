from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from timepiece import forms
from timepiece.tests.base import TimepieceDataTestCase

from timepiece.crm.models import UserProfile


class EditSettingsTest(TimepieceDataTestCase):

    def setUp(self):
        super(EditSettingsTest, self).setUp()
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
        self.assertRedirects(response, reverse('dashboard'))
        self.user = User.objects.get(pk=self.user.pk)
        for k, v in data.iteritems():
            value = getattr(self.user, k)
            self.assertEquals(value, v)
        next = reverse('clock_in')
        next_query_url = '%s?next=%s' % (self.url, next)
        data = {
            'first_name': 'Terry',
            'last_name': 'Pratchet',
            'email': 'test@caktusgroup.com',
        }
        response = self.edit_profile(next_query_url, data)
        self.assertRedirects(response, next)
        self.profile = UserProfile.objects.get(user=self.user)


class EditUserTest(TimepieceDataTestCase):

    def setUp(self):
        super(EditUserTest, self).setUp()
        self.url = reverse('edit_user', args=(self.user.pk,))
        self.data = {
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'is_active': self.user.is_active,
            'is_superuser': self.user.is_superuser
        }

    def login_with_permission(self):
        user = self.create_user('admin', 'e@e.com', 'abc', is_superuser=True,
                is_staff=True)
        self.client.login(username='admin', password='abc')

    def test_edit_user(self):
        """
        A user should be able to successfully edit someone if
        the information is correct
        """
        self.login_with_permission()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

        self.data['password_one'] = 'password'
        self.data['password_two'] = 'password'

        response = self.client.post(self.url, data=self.data)
        # User was updated, so self.user contains incorrect password
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.check_password('password'))

    def test_edit_user_invalid(self):
        """
        If passwords do not match, user should be returned to the
        form and an error should be displayed
        """
        self.login_with_permission()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

        self.data['password_one'] = 'password1'
        self.data['password_two'] = 'password2'

        response = self.client.post(self.url, data=self.data)
        form = response.context['form']
        self.assertEquals(form.non_field_errors(), ['Passwords Must Match.'])

    def test_edit_user_groups(self):
        """
        A user should be able to successfully edit someone if the information
        is correct
        """
        self.login_with_permission()
        group1 = self.create_auth_group()
        group2 = self.create_auth_group()
        self.data['groups'] = (group1.id,)
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=self.user.pk)
        user_groups = user.groups.all()
        self.assertTrue(group1 in user_groups)
        self.assertTrue(group2 not in user_groups)
