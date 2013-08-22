from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse

from timepiece.tests import factories
from timepiece.tests.base import TimepieceDataTestCase, ViewTestMixin


__all__ = ['TestDeleteUserView', 'TestEditUserView', 'TestEditSettingsView']


class TestDeleteUserView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'delete_user'
    template_name = 'timepiece/delete_object.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.perm = Permission.objects.get(codename='delete_user')
        self.user.user_permissions.add(self.perm)
        self.login_user(self.user)

        self.obj = factories.UserFactory.create()

        self.url_kwargs = {'user_id': self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required to delete a user."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(User.objects.count(), 2)

    def test_post_no_permission(self):
        """Permission is required to delete a user."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(User.objects.count(), 2)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(User.objects.count(), 2)

    def test_post(self):
        """POST should delete the user."""
        response = self._post()
        self.assertEquals(User.objects.count(), 1)


class TestEditUserView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'edit_user'
    template_name = 'timepiece/user/create_edit.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.perm = Permission.objects.get(codename='change_user')
        self.user.user_permissions.add(self.perm)
        self.login_user(self.user)

        self.obj = factories.UserFactory.create()
        self.url_kwargs = {'user_id': self.obj.pk}

    @property
    def post_data(self):
        return {
            'username': self.obj.username,
            'first_name': self.obj.first_name,
            'last_name': self.obj.last_name,
            'email': self.obj.email,
            'is_active': self.obj.is_active,
            'is_staff': self.obj.is_staff,
            'groups': self.obj.groups.values_list('pk', flat=True),
        }

    def test_get_no_permission(self):
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_post_no_permission(self):
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)

    def test_get(self):
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

    def test_post_valid(self):
        data = self.post_data
        data.update({'first_name': 'hello'})
        response = self._post(data=data)
        self.assertRedirectsNoFollow(response, self.obj.get_absolute_url())
        updated_user = User.objects.get(pk=self.obj.pk)
        self.assertEquals(updated_user.first_name, data['first_name'])

    def test_matching_passwords(self):
        data = {'password_one': 'aaa', 'password_two': 'bbb'}
        response = self._post(data=data)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        form = response.context['form']
        self.assertFalse(form.is_valid())

    def test_edit_groups(self):
        groups = [factories.GroupFactory.create(),
                factories.GroupFactory.create()]
        data = self.post_data
        data.update({'groups': [g.pk for g in groups]})
        response = self._post(data=data)
        self.assertRedirectsNoFollow(response, self.obj.get_absolute_url())
        updated_user = User.objects.get(pk=self.obj.pk)
        self.assertEquals(updated_user.groups.count(), 2)
        self.assertTrue(groups[0] in updated_user.groups.all())
        self.assertTrue(groups[1] in updated_user.groups.all())


class TestEditSettingsView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'edit_settings'
    template_name = 'timepiece/user/settings.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.login_user(self.user)

        self.post_data = {
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'hello@example.com',
        }

    def test_get(self):
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

    def test_post_valid(self):
        response = self._post()
        self.assertRedirectsNoFollow(response, reverse('dashboard'))

        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.iteritems():
            self.assertEquals(getattr(updated_user, k), v)

    def test_redirect_to_next(self):
        response = self._post(get_kwargs={'next': '/hello/'})
        self.assertRedirectsNoFollow(response, '/hello/')

        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.iteritems():
            self.assertEquals(getattr(updated_user, k), v)
